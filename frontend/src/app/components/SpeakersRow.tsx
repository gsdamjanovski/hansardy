"use client";

import SpeakerCard from "./SpeakerCard";
import type { SpeakerProfile } from "../types";

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
