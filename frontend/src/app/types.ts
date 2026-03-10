export interface Source {
  id: string;
  text: string;
  chamber: string;
  sitting_date: string;
  speakers: string;
  parliament_no: number;
  source_file: string;
  score: number;
}

export interface SpeakerProfile {
  id: string;
  canonical_name: string;
  display_name: string;
  primary_party: string;
  era: string;
  appearances: number;
  chambers: string[];
  year_start: number | null;
  year_end: number | null;
  date_of_birth: string | null;
  date_of_death: string | null;
  gender: string | null;
  notable: string | null;
  electorates: string[];
  photo_url: string | null;
  aph_id: string | null;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  speakers?: Record<string, SpeakerProfile>;
  queryType?: string;
}
