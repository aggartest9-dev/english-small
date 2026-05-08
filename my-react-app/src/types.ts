export enum QuestionFormat {
  MCQ = "mcq",
  FILL_BLANK = "fill_blank",
  LONG = "long",
  SHORT = "short",
  SPEAKING = "speaking_task",
}

export enum ResponseType {
  OPTION = "option",
  TEXT = "text",
  AUDIO = "audio",
}

export interface Option {
  id: number;
  text: string;
  order: number;
  explanation?: string;
}

export interface Question {
  id: number;
  format_type: QuestionFormat; // Use QuestionFormat enum here
  format_label?: string;
  response_type: ResponseType; // Use ResponseType enum here
  response_label?: string;
  difficulty?: string;
  difficulty_label?: string;
  text: string;

  prompt_audio: string | null;
  prompt_video: string | null;
  prompt_image: string | null;

  timestamp_start: number | null; // In seconds (use number for safer frontend logic)
  timestamp_end: number | null;

  auto_pause?: boolean;
  resume_after_submit?: boolean;

  marks: number;
  order: number;
  is_required: boolean;

  options: Option[];

  preAudio?: string | null;
  postAudio?: string | null;

  processed_pre_url?: string | null;
  processed_post_url?: string | null;

  explanation?: string | null;
}

export interface MediaItem {
  id: number;
  media_type: string;
  media_type_label: string;
  title: string;

  file_url: string | null;
  subtitle_url?: string | null;
  thumbnail_url?: string | null;

  is_primary: boolean;
  duration_seconds?: number | null;
  order: number;

  text_content?: string;
  processed_url?: string | null;
}

export interface SessionBlock {
  id: number;
  section: number;
  order: number;

  block_type: string;
  block_type_label: string;

  title: string;
  description: string;
  text_content: string;

  estimated_seconds: number | null;
  is_required: boolean;

  unlock_after_completion?: boolean;

  media_items: MediaItem[];
  questions: Question[];

  preAudio?: string | null;
  processed_url?: string | null;
}

export interface ContentSession {
  id: number;
  title: string;
  description: string;
  level: string;
  day: number;

  objectives: {
    id: number;
    text: string;
    order: number;
  }[];

  blocks: SessionBlock[];
}

export interface UserAnswer {
  question_id: number;
  selected_option_id?: number;
  text_answer?: string;
  audio_blob?: Blob;
  is_correct?: boolean;
}