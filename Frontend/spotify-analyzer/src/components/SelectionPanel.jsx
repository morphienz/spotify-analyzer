function SelectionPanel({
  genres,
  selectedGenres,
  excludedTrackIds,
  toggleExclude
}) {
  const visibleGenres = [...selectedGenres].filter((genre) => genres[genre]);

  if (visibleGenres.length === 0) {
    return (
      <div className="text-gray-400 mt-8">
        Tür seçerek detaylı şarkı listesi görebilirsin.
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl mt-8 space-y-8">
      {visibleGenres.map((genre) => (
        <div key={genre}>
          <h3 className="text-lg font-bold text-green-400 mb-2">{genre}</h3>
          <div className="grid gap-2 md:grid-cols-2">
            {genres[genre].map((track) => (
              <div
                key={track.id}
                className={`flex justify-between items-center p-3 rounded-lg border ${
                  excludedTrackIds.includes(track.id)
                    ? "bg-gray-800 border-red-500 text-red-400 line-through"
                    : "bg-gray-900 border-gray-700"
                }`}
              >
                <div className="flex-1">
                  <div className="font-medium">{track.name}</div>
                  <div className="text-sm text-gray-400">{track.artist}</div>
                </div>
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
        </div>
      ))}
    </div>
  );
}

export default SelectionPanel;
