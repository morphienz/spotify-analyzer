import { Pie } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

function GenreChart({ breakdown, onSelectGenre, selectedGenres }) {
  const labels = Object.keys(breakdown);
  const dataCounts = labels.map((label) => breakdown[label].count);

  const colors = [
    "#1DB954", "#FF6384", "#36A2EB", "#FFCE56",
    "#9966FF", "#E7E9ED", "#00FFFF", "#FF4500",
    "#2E8B57", "#DA70D6", "#FFD700", "#8A2BE2"
  ];

  const chartData = {
    labels,
    datasets: [
      {
        data: dataCounts,
        backgroundColor: colors,
      },
    ],
  };

  const chartOptions = {
    plugins: {
      legend: {
        display: true,
        labels: {
          color: "#ffffff",
        },
        onClick: (e, legendItem) => {
          const genre = legendItem.text;
          onSelectGenre(genre);
        }
      },
    },
  };

  return (
    <div className="w-full max-w-xl mb-8">
      <h2 className="text-xl font-semibold text-center mb-4 text-green-300">Tür Dağılımı</h2>
      <Pie data={chartData} options={chartOptions} />
      <div className="mt-4 flex flex-wrap gap-2 justify-center">
        {labels.map((genre) => (
          <span
            key={genre}
            onClick={() => onSelectGenre(genre)}
            className={`cursor-pointer px-3 py-1 rounded-full text-sm border ${
              selectedGenres.has(genre)
                ? "bg-green-500 text-black"
                : "bg-gray-800 text-white border-gray-600"
            }`}
          >
            {genre}
          </span>
        ))}
      </div>
    </div>
  );
}

export default GenreChart;
