import { useState } from "react";
function SelectionPanel({
  genres,
  selectedGenres,
  excludedTrackIds,
  toggleExclude,
  manualAssignments,
  setManualAssignments,
}) {
  const visibleGenres = [...selectedGenres].filter((genre) => genres[genre]);
  const [openGenres, setOpenGenres] = useState([]);

  const toggleOpen = (genre) => {
    setOpenGenres((prev) =>
      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
    );
  };

  const handleAssign = (id, genre) => {
    setManualAssignments((prev) => ({ ...prev, [id]: genre }));
  };

  if (visibleGenres.length === 0) {
    return (
      <div className="text-gray-400 mt-8">
        Tür seçerek detaylı şarkı listesi görebilirsin.
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl mt-8 space-y-4">
      {visibleGenres.map((genre) => (
        <div key={genre} className="bg-gray-900 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleOpen(genre)}
            className="w-full text-left px-4 py-2 bg-gray-800 hover:bg-gray-700 font-bold"
          >
            {genre}
          </button>
          {openGenres.includes(genre) && (
            <div className="p-3 space-y-2 max-h-60 overflow-y-auto">
              {genres[genre].map((track) => (
                <div
                  key={track.id}
                  className={`flex justify-between items-center p-2 rounded border ${
                    excludedTrackIds.includes(track.id)
                      ? "bg-gray-800 border-red-500 text-red-400 line-through"
                      : "bg-gray-900 border-gray-700"
                  }`}
                >
                  <div className="flex-1 mr-2">
                    <div className="font-medium">{track.name}</div>
                    <div className="text-sm text-gray-400">{track.artist}</div>
                  </div>
                  {genre === "unknown" && (
                    <select
                      value={manualAssignments[track.id] || ""}
                      onChange={(e) => handleAssign(track.id, e.target.value)}
                      className="bg-gray-700 text-white text-sm rounded mr-2"
                    >
                      <option value="">Tür Seç</option>
                      {Object.keys(genres)
                        .filter((g) => g !== "unknown")
                        .map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                    </select>
                  )}
                  {track.preview_url && (
                    <audio
                      controls
                      src={track.preview_url}
                      className="w-32 mr-2"
                    />
                  )}
                  <button
                    onClick={() => toggleExclude(track.id)}
                    className={`text-sm font-bold px-3 py-1 rounded-full ${
                      excludedTrackIds.includes(track.id)
                        ? "bg-red-500 text-white"
                        : "bg-gray-600 text-white"
                    }`}
                  >
                    {excludedTrackIds.includes(track.id) ? "Geri Al" : "Hariç Tut"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default SelectionPanel;
