"""Comprehensive progress tracking and resume functionality."""

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import logging

@dataclass
class SlideProgress:
    """Individual slide processing state."""
    slide_number: int
    completed: bool
    character_count: int
    completion_time: Optional[datetime] = None
    is_validated: bool = False
    error_message: Optional[str] = None

@dataclass 
class ProcessingState:
    """Complete processing state for resume capability."""
    file_path: str
    total_slides: int
    completed_slides: int
    slide_progress: List[SlideProgress]
    last_validated_slide: int
    output_path: str
    start_time: datetime
    last_update: datetime
    processing_mode: str  # 'single' or 'batch'
    prompt_checksum: str  # Validate prompt hasn't changed
    config_checksum: str  # Validate config hasn't changed

class ProgressManager:
    """Manages processing progress with robust resume capability."""
    
    def __init__(self, output_path: Optional[Path], mode: str, file_path: Path):
        self.mode = mode
        self.file_path = file_path
        self.output_path = output_path
        self.state_file = self._get_state_file_path()
        self.logger = logging.getLogger(__name__)
        
    def _get_state_file_path(self) -> Path:
        """Generate state file path based on mode and output location."""
        if self.mode == 'single':
            if self.output_path:
                return self.output_path.parent / f".slide_extract_progress_{self.output_path.stem}.json"
            else:
                return Path(f".slide_extract_progress_{self.file_path.stem}.json")
        else:  # batch mode - each file gets its own progress file
            if self.output_path:
                return self.output_path.parent / f".slide_extract_progress_{self.output_path.stem}.json"
            else:
                return Path(f".slide_extract_progress_{self.file_path.stem}.json")
    
    def has_incomplete_work(self) -> bool:
        """Check if there's resumable work from previous run."""
        return self.state_file.exists() and self._validate_state_file()
    
    def _validate_state_file(self) -> bool:
        """Validate state file integrity and compatibility."""
        try:
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)
            
            # Validate required fields exist
            required_fields = ['file_path', 'total_slides', 'slide_progress']
            if not all(field in state_data for field in required_fields):
                self.logger.warning("State file missing required fields")
                return False
                
            # Validate file still exists
            if not Path(state_data['file_path']).exists():
                self.logger.warning("Original file no longer exists")
                return False
                
            return True
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"State file validation failed: {e}")
            return False
    
    def get_resume_point(self) -> tuple[int, ProcessingState]:
        """Determine safe resume point after validation."""
        state = self.load_state()
        
        # Find last validated complete slide
        last_safe_slide = 0
        for slide in state.slide_progress:
            if slide.completed and slide.is_validated:
                last_safe_slide = slide.slide_number
        
        # Check if last slide needs cleanup
        if state.completed_slides > last_safe_slide:
            self.logger.info(f"Detected incomplete slide {state.completed_slides}, will clean up and resume from {last_safe_slide + 1}")
            self._cleanup_incomplete_output(last_safe_slide)
        
        return last_safe_slide + 1, state
    
    def _cleanup_incomplete_output(self, last_safe_slide: int) -> None:
        """Remove incomplete content from output file."""
        if not self.output_path or not self.output_path.exists():
            return
            
        try:
            with open(self.output_path, 'r') as f:
                content = f.read()
            
            # Find the marker for the last safe slide
            # This assumes our output format has slide markers
            slide_markers = []
            for i, line in enumerate(content.split('\n')):
                if line.startswith('**Slide Number:**'):
                    slide_num = int(line.split('**Slide Number:**')[1].strip())
                    slide_markers.append((slide_num, i))
            
            # Find cutoff point
            cutoff_line = 0
            for slide_num, line_num in slide_markers:
                if slide_num <= last_safe_slide:
                    cutoff_line = line_num
            
            # Truncate file to last safe point
            if cutoff_line > 0:
                lines = content.split('\n')
                truncated_content = '\n'.join(lines[:cutoff_line])
                with open(self.output_path, 'w') as f:
                    f.write(truncated_content)
                    
                self.logger.info(f"Cleaned up output file, removed content after slide {last_safe_slide}")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup incomplete output: {e}")
    
    def checkpoint_slide(self, slide_num: int, content: str, slide_content) -> None:
        """Save progress checkpoint after successful slide completion."""
        state = self.load_state() if self.state_file.exists() else self._create_initial_state()
        
        # Update slide progress
        slide_progress = SlideProgress(
            slide_number=slide_num,
            completed=True,
            character_count=len(content),
            completion_time=datetime.now(),
            is_validated=self._validate_slide_content(content),
            error_message=None
        )
        
        # Update or add slide progress
        existing_slide = next((s for s in state.slide_progress if s.slide_number == slide_num), None)
        if existing_slide:
            state.slide_progress[state.slide_progress.index(existing_slide)] = slide_progress
        else:
            state.slide_progress.append(slide_progress)
        
        # Update overall state
        state.completed_slides = slide_num
        state.last_validated_slide = slide_num if slide_progress.is_validated else state.last_validated_slide
        state.last_update = datetime.now()
        
        # Save state
        self.save_state(state)
        
        # Append to output file if in streaming mode
        if self.output_path and self.mode == 'single':
            self._append_to_output(content)
        
        self.logger.debug(f"Checkpointed slide {slide_num} ({len(content)} chars)")
    
    def _validate_slide_content(self, content: str) -> bool:
        """Validate slide content completeness and structure."""
        required_sections = [
            '**Slide Number:**',
            '**Slide Text:**', 
            '**Slide Images/Diagrams:**',
            '**Slide Topics:**',
            '**Slide Narration:**'
        ]
        
        return all(section in content for section in required_sections)
    
    def _append_to_output(self, content: str) -> None:
        """Append content to output file."""
        try:
            with open(self.output_path, 'a', encoding='utf-8') as f:
                f.write(content)
                f.write('\n---\n\n')
        except Exception as e:
            self.logger.error(f"Failed to append to output file: {e}")
    
    def _create_initial_state(self) -> ProcessingState:
        """Create initial processing state."""
        return ProcessingState(
            file_path=str(self.file_path),
            total_slides=0,  # Will be updated when known
            completed_slides=0,
            slide_progress=[],
            last_validated_slide=0,
            output_path=str(self.output_path) if self.output_path else "",
            start_time=datetime.now(),
            last_update=datetime.now(),
            processing_mode=self.mode,
            prompt_checksum="",  # Will be set when prompt is loaded
            config_checksum=""   # Will be set when config is loaded
        )
    
    def save_state(self, state: ProcessingState) -> None:
        """Persist processing state to disk."""
        try:
            # Convert datetime objects to ISO strings for JSON serialization
            state_dict = asdict(state)
            state_dict['start_time'] = state.start_time.isoformat()
            state_dict['last_update'] = state.last_update.isoformat()
            
            # Convert slide progress datetime objects
            for slide in state_dict['slide_progress']:
                if slide.get('completion_time'):
                    slide['completion_time'] = slide['completion_time'].isoformat()
            
            with open(self.state_file, 'w') as f:
                json.dump(state_dict, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    def load_state(self) -> ProcessingState:
        """Load processing state from disk."""
        try:
            with open(self.state_file, 'r') as f:
                state_dict = json.load(f)
            
            # Convert ISO strings back to datetime objects
            state_dict['start_time'] = datetime.fromisoformat(state_dict['start_time'])
            state_dict['last_update'] = datetime.fromisoformat(state_dict['last_update'])
            
            # Convert slide progress datetime objects
            slide_progress = []
            for slide_data in state_dict['slide_progress']:
                if slide_data.get('completion_time'):
                    slide_data['completion_time'] = datetime.fromisoformat(slide_data['completion_time'])
                slide_progress.append(SlideProgress(**slide_data))
            
            state_dict['slide_progress'] = slide_progress
            
            return ProcessingState(**state_dict)
            
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            return self._create_initial_state()
    
    def record_slide_error(self, slide_num: int, error_message: str) -> None:
        """Record error for a specific slide."""
        state = self.load_state() if self.state_file.exists() else self._create_initial_state()
        
        # Update slide progress with error
        slide_progress = SlideProgress(
            slide_number=slide_num,
            completed=False,
            character_count=0,
            completion_time=datetime.now(),
            is_validated=False,
            error_message=error_message
        )
        
        # Update or add slide progress
        existing_slide = next((s for s in state.slide_progress if s.slide_number == slide_num), None)
        if existing_slide:
            state.slide_progress[state.slide_progress.index(existing_slide)] = slide_progress
        else:
            state.slide_progress.append(slide_progress)
        
        state.last_update = datetime.now()
        self.save_state(state)
        
        self.logger.error(f"Recorded error for slide {slide_num}: {error_message}")
    
    def cleanup_state(self) -> None:
        """Remove state file after successful completion."""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
                self.logger.info("Cleaned up progress state file")
        except Exception as e:
            self.logger.error(f"Failed to cleanup state file: {e}")
    
    def update_total_slides(self, total: int) -> None:
        """Update total slides count in state."""
        if self.state_file.exists():
            state = self.load_state()
            state.total_slides = total
            state.last_update = datetime.now()
            self.save_state(state)