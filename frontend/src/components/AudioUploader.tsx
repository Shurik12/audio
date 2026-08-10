import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Mic, X, FileAudio, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

interface AudioUploaderProps {
  onFileUpload: (file: File) => void;
  isLoading?: boolean;
  accept?: string[];
  maxSize?: number;
}

const AudioUploader: React.FC<AudioUploaderProps> = ({
  onFileUpload,
  isLoading = false,
  accept = ['audio/wav', 'audio/mp3', 'audio/m4a', 'audio/flac'],
  maxSize = 50 * 1024 * 1024, // 50MB
}) => {
  const [file, setFile] = useState<File | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const selectedFile = acceptedFiles[0];
    if (selectedFile) {
      if (selectedFile.size > maxSize) {
        toast.error(`File too large. Max size: ${maxSize / 1024 / 1024}MB`);
        return;
      }
      setFile(selectedFile);
      onFileUpload(selectedFile);
      toast.success(`File loaded: ${selectedFile.name}`);
    }
  }, [maxSize, onFileUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: accept.reduce((acc, type) => ({ ...acc, [type]: [] }), {}),
    maxSize,
    multiple: false,
  });

  const removeFile = () => {
    setFile(null);
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer
          transition-all duration-200 ease-in-out
          ${isDragActive 
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' 
            : 'border-gray-300 dark:border-gray-600 hover:border-primary-400 dark:hover:border-primary-500'
          }
          ${isLoading ? 'opacity-50 pointer-events-none' : ''}
        `}
      >
        <input {...getInputProps()} disabled={isLoading} />
        
        {isLoading ? (
          <div className="flex flex-col items-center">
            <Loader2 className="w-16 h-16 text-primary-500 animate-spin mb-4" />
            <p className="text-gray-600 dark:text-gray-400">Processing audio...</p>
          </div>
        ) : file ? (
          <div className="flex flex-col items-center">
            <FileAudio className="w-16 h-16 text-primary-500 mb-4" />
            <p className="text-lg font-medium text-gray-900 dark:text-white">{file.name}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
            <button
              onClick={(e) => {
                e.stopPropagation();
                removeFile();
              }}
              className="mt-4 px-4 py-2 text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
            >
              <X className="w-4 h-4 inline mr-1" />
              Remove file
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <Upload className="w-16 h-16 text-gray-400 dark:text-gray-500 mb-4" />
            <p className="text-lg font-medium text-gray-900 dark:text-white">
              Drag & drop audio file here
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              or click to browse
            </p>
            <div className="mt-4 flex flex-wrap gap-2 justify-center">
              {accept.map((type) => (
                <span
                  key={type}
                  className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full"
                >
                  {type.split('/')[1].toUpperCase()}
                </span>
              ))}
            </div>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-4">
              Max size: {maxSize / 1024 / 1024}MB
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AudioUploader;