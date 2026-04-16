import {
  Github,
  GitBranch,
  FolderGit2,
  Lock,
  Star,
  GitFork,
  ExternalLink,
  Clock,
} from "lucide-react";

const getTimeDiff = (date) => {
  if (!date) return null;
  const now = new Date();
  const past = new Date(date);
  const diffInDays = Math.floor((now - past) / (1000 * 60 * 60 * 24));
  if (diffInDays === 0) return "today";
  if (diffInDays === 1) return "yesterday";
  if (diffInDays < 7) return `${diffInDays} days ago`;
  if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} weeks ago`;
  return `${Math.floor(diffInDays / 30)} months ago`;
};

const PlatformIcon = ({ platform, className = "w-4 h-4" }) => {
  if (platform === "github") return <Github className={className} />;
  return <GitBranch className={className} />;
};

const getPlatformLabel = (platform) => {
  if (platform === "github") return "GitHub";
  if (platform === "gitlab") return "GitLab.com";
  return "GitLab Self-Hosted";
};

const RepositoryCard = ({
  repo,
  platform: platformOverride,
  onClick,
  onCollect,
  showWorkspace = false,
}) => {
  const platform = repo.platform ?? platformOverride;
  const timeDiff = getTimeDiff(repo.updated_at);

  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl border border-gray-200 p-4 sm:p-5 hover:shadow-lg transition-shadow flex flex-col ${
        onClick ? "cursor-pointer" : ""
      }`}
    >
      <div className="flex-1">
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center shrink-0">
              {platform ? (
                <PlatformIcon platform={platform} className="w-5 h-5" />
              ) : (
                <FolderGit2 className="w-5 h-5 text-gray-600" />
              )}
            </div>
            <div className="min-w-0">
              <p
                className="font-semibold text-gray-900 truncate text-sm sm:text-base"
                title={repo.full_name ?? repo.name}
              >
                {repo.name}
              </p>
              {showWorkspace && repo.workspace_name && (
                <p className="text-xs text-gray-500 truncate">{repo.workspace_name}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            {repo.is_private && <Lock className="w-3.5 h-3.5 text-gray-400" />}
            {repo.web_url && (
              <a
                href={repo.web_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="p-1 hover:bg-gray-100 rounded"
                title="Open repository"
              >
                <ExternalLink className="w-3.5 h-3.5 text-gray-400" />
              </a>
            )}
          </div>
        </div>

        {repo.description ? (
          <p className="text-xs sm:text-sm text-gray-500 mb-3 line-clamp-2">
            {repo.description}
          </p>
        ) : (
          <p className="text-xs sm:text-sm text-gray-400 italic mb-3">No description provided.</p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 text-xs sm:text-sm text-gray-500">
          {repo.language && (
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 bg-blue-500 rounded-full" />
              <span>{repo.language}</span>
            </div>
          )}
          {!repo.language && platform && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 rounded-full">
              <PlatformIcon platform={platform} className="w-3 h-3" />
              {getPlatformLabel(platform)}
            </span>
          )}
          <div className="flex items-center gap-3 ml-auto">
            {repo.stars_count > 0 && (
              <span className="flex items-center gap-1">
                <Star className="w-3.5 h-3.5" />
                {repo.stars_count}
              </span>
            )}
            {repo.forks_count > 0 && (
              <span className="flex items-center gap-1">
                <GitFork className="w-3.5 h-3.5" />
                {repo.forks_count}
              </span>
            )}
          </div>
        </div>

        {timeDiff && (
          <div className="flex items-center gap-1.5 text-xs text-gray-400 mt-2">
            <Clock className="w-3.5 h-3.5 shrink-0" />
            <span>Updated {timeDiff}</span>
          </div>
        )}
      </div>

      {onCollect && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCollect(repo);
            }}
            className="w-full text-xs py-1.5 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition"
          >
            Collect
          </button>
        </div>
      )}
    </div>
  );
};

export default RepositoryCard;
