"use client";

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

const PARTY_COLORS: Record<string, string> = {
  Labor: "text-red-700",
  Liberal: "text-blue-700",
  Nationals: "text-emerald-700",
  Greens: "text-green-700",
};

export default function SpeakerCard({
  profile,
}: {
  profile: SpeakerProfile;
}) {
  const partyColor = PARTY_COLORS[profile.primary_party] || "text-stone-600";

  const yearRange =
    profile.year_start && profile.year_end
      ? `${profile.year_start}–${profile.year_end}`
      : profile.year_start
        ? `${profile.year_start}–`
        : null;

  const electorate = profile.electorates.length > 0 ? profile.electorates[0] : null;

  const aphUrl = profile.aph_id
    ? `https://www.aph.gov.au/Senators_and_Members/Parliamentarian?MPID=${profile.aph_id}`
    : null;

  return (
    <div className="min-w-[220px] max-w-[260px] flex-shrink-0 border border-rose-200 rounded-xl p-3 bg-white hover:border-rose-300 transition-colors">
      <div className="flex items-start gap-2.5">
        {profile.photo_url ? (
          <img
            src={profile.photo_url}
            alt={profile.display_name}
            className="w-9 h-9 rounded-full object-cover flex-shrink-0 border border-stone-200"
          />
        ) : (
          <div className="w-9 h-9 rounded-full bg-stone-100 border border-stone-200 flex items-center justify-center flex-shrink-0">
            <span className="text-stone-400 text-xs font-medium">
              {profile.display_name
                .split(" ")
                .map((w) => w[0])
                .slice(0, 2)
                .join("")}
            </span>
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="font-medium text-stone-900 text-xs truncate leading-tight">
            {aphUrl ? (
              <a
                href={aphUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:underline"
              >
                {profile.display_name}
              </a>
            ) : (
              profile.display_name
            )}
          </p>
          <p className="text-[11px] leading-snug mt-0.5">
            <span className={`font-medium ${partyColor}`}>
              {profile.primary_party}
            </span>
            {electorate && (
              <>
                <span className="text-stone-300 mx-1">&middot;</span>
                <span className="text-stone-500 truncate">{electorate}</span>
              </>
            )}
            {yearRange && (
              <>
                <span className="text-stone-300 mx-1">&middot;</span>
                <span className="text-stone-500">{yearRange}</span>
              </>
            )}
          </p>
        </div>
      </div>
      {profile.notable && (
        <p className="text-[11px] text-stone-500 mt-1.5 leading-snug line-clamp-2">
          {profile.notable}
        </p>
      )}
    </div>
  );
}
