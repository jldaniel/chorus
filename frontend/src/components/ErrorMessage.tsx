interface Props {
  message: string;
  onRetry?: () => void;
}

export default function ErrorMessage({ message, onRetry }: Props) {
  return (
    <div className="flex flex-col items-center gap-3 p-8 text-gray-400">
      <p className="text-red-400">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded bg-gray-700 px-3 py-1.5 text-sm text-gray-200 hover:bg-gray-600"
        >
          Retry
        </button>
      )}
    </div>
  );
}
