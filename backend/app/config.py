# app/config.py
from pydantic_settings import BaseSettings
from typing import Dict, List
import json


class Settings(BaseSettings):
    supabase_url:         str
    supabase_service_key: str
    groq_api_key:         str = ""
    mistral_api_key:      str = ""
    app_env:              str = "development"
    cors_origins:         str = "http://localhost:5173"

    mistral_model:                   str = "mistral-small-latest"
    mistral_temperature:             float = 0.0
    mistral_max_retries:             int = 3
    mistral_retry_base_delay_sec:    float = 0.6

    whisper_model:                   str = "whisper-large-v3-turbo"
    whisper_language:                str = "auto"

    softskills_parallel_analysis: bool = True  
    softskills_global_analysis: bool = False   
    softskills_max_skills: int = 5 

    segment_max_transcript_chars:    int = 999999
    segment_llm_attempts:            int = 2
    segment_no_answer_placeholder:   str = "[No answer extracted]"

    text_min_answer_words:           int = 3
    text_relevance_max_workers:      int = 5
    soft_skills_max_transcript_chars:int = 8000

    transcript_split_min_chars:      int = 300
    transcript_fillers:              str = "um,uh,uhh,er,ah,you know,so uh,uh so,i mean,euh,ben,alors"
    transcript_interviewer_cues:     str = "okay um,okay so,alright,what are the,can you tell,could you,why do you,how do you,next question,d accord,alors,pouvez vous,peux tu,parlez moi,prochaine question"

    video_frame_fps_target:          int = 3
    video_min_high_quality_frames:   int = 10
    video_face_detect_reliable_pct:  float = 40.0
    video_quality_confidence_threshold: float = 0.5
    video_emotion_noise_floor:       float = 0.05
    video_emotion_dampening_json:    str = '{"contempt": 0.05, "disgust": 0.10, "anger": 0.30, "fear": 0.40, "surprise": 0.40}'
    video_score_calibration_json:    str = "{}"

    defendability_min_questions:     int = 2
    defendability_min_answered_ratio:float = 0.6
    defendability_min_soft_skills:   int = 1

    video_min_detected_pct_strong:   float = 70.0
    video_min_detected_pct_usable:   float = 40.0
    video_timeline_window_sec:           float = 3.0
    video_timeline_switch_confidence_min: float = 35.0

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def transcript_fillers_list(self) -> List[str]:
        return [item.strip() for item in self.transcript_fillers.split(",") if item.strip()]

    @property
    def transcript_interviewer_cues_list(self) -> List[str]:
        return [item.strip() for item in self.transcript_interviewer_cues.split(",") if item.strip()]

    @property
    def video_emotion_dampening(self) -> Dict[str, float]:
        try:
            value = json.loads(self.video_emotion_dampening_json)
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    @property
    def video_score_calibration(self) -> Dict:
        try:
            value = json.loads(self.video_score_calibration_json)
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra environment variables not defined in Settings


settings = Settings()