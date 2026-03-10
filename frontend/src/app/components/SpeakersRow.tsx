"use client";

import SpeakerCard from "./SpeakerCard";

interface SpeakerProfile {
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

export default function SpeakersRow({
  speakers,
}: {
  speakers: Record<string, SpeakerProfile>;
}) {
  const profiles = Object.values(speakers);
  if (profiles.length === 0) return null;

  return (
    <div className="mb-3">
      <p className="text-[11px] font-medium text-stone-400 uppercase tracking-wide mb-1.5">
        Speakers
      </p>
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {profiles.map((profile) => (
          <SpeakerCard key={profile.id} profile={profile} />
        ))}
      </div>
    </div>
  );
}
