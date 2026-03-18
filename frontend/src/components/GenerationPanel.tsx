import { useState, useEffect, useCallback } from 'react';
import type { Target, Narrative, DriveUploadResponse, ArticleResponse, PublishResponse } from '../api';
import {
  generatePrompt,
  generateImage,
  generateVideo,
  generateArticle,
  publishArticle,
  checkVideoStatus,
  getMediaUrl,
  getDownloadUrl,
  getArticleUrl,
  uploadToDrive,
} from '../api';

interface GenerationPanelProps {
  target: Target;
  narrative: Narrative;
  onReset: () => void;
}

type GenerationType = 'video' | 'article';
type GenerationStatus = 'idle' | 'generating-prompt' | 'prompt-ready' | 'generating-media' | 'generating-article' | 'polling-video' | 'complete' | 'error';

export default function GenerationPanel({ target, narrative, onReset }: GenerationPanelProps) {
  const [genType, setGenType] = useState<GenerationType>('article');
  const [status, setStatus] = useState<GenerationStatus>('idle');
  const [prompt, setPrompt] = useState('');

  // Article dual prompts
  const [imagePrompt, setImagePrompt] = useState('');
  const [articlePrompt, setArticlePrompt] = useState('');

  const [mediaUrl, setMediaUrl] = useState('');
  const [filename, setFilename] = useState('');
  const [error, setError] = useState('');
  const [pollingProgress, setPollingProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<DriveUploadResponse | null>(null);
  const [uploadError, setUploadError] = useState('');

  // Article-specific state
  const [articleData, setArticleData] = useState<ArticleResponse | null>(null);
  const [publishing, setPublishing] = useState(false);
  const [publishResult, setPublishResult] = useState<PublishResponse | null>(null);

  // Auto-generate prompt on mount and when genType changes
  useEffect(() => {
    const abortController = new AbortController();

    // Debounce: wait 100ms before firing to prevent rapid tab switching issues
    const timeoutId = setTimeout(() => {
      handleGeneratePrompt(abortController.signal);
    }, 100);

    // Cleanup: cancel request and timeout on unmount or genType change
    return () => {
      clearTimeout(timeoutId);
      abortController.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [genType]);

  const handleGeneratePrompt = async (signal?: AbortSignal) => {
    setStatus('generating-prompt');
    setError('');
    try {
      const result = await generatePrompt(target.id, narrative.id, genType, signal);

      // Handle dual prompts for articles
      if (genType === 'article' && result.image_prompt && result.article_prompt) {
        setImagePrompt(result.image_prompt);
        setArticlePrompt(result.article_prompt);
      } else {
        setPrompt(result.prompt);
      }

      setStatus('prompt-ready');
    } catch (err: any) {
      // Ignore aborted requests (user switched tabs)
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
        return;
      }
      setError(err.response?.data?.detail || 'Failed to generate prompt');
      setStatus('error');
    }
  };

  const handleGenerate = async () => {
    setStatus('generating-media');
    setError('');
    setMediaUrl('');
    setFilename('');

    try {
      if (genType === 'video') {
        const result = await generateVideo(prompt);
        setStatus('polling-video');
        pollVideoStatus(result.operation_id);
      } else if (genType === 'article') {
        setStatus('generating-article');
        const result = await generateArticle(target.id, narrative.id, imagePrompt, articlePrompt);
        setArticleData(result);
        setStatus('complete');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to generate ${genType}`);
      setStatus('error');
    }
  };

  const pollVideoStatus = useCallback(async (operationId: string) => {
    let attempts = 0;
    const maxAttempts = 60; // 10 minutes max

    const poll = async () => {
      attempts++;
      setPollingProgress(Math.min((attempts / maxAttempts) * 100, 95));

      try {
        const result = await checkVideoStatus(operationId);

        if (result.status === 'complete' && result.video_url) {
          setMediaUrl(getMediaUrl(result.video_url));
          setFilename(result.filename || 'video.mp4');
          setStatus('complete');
          setPollingProgress(100);
          return;
        }

        if (result.status === 'failed') {
          setError(result.error || 'Video generation failed');
          setStatus('error');
          return;
        }

        // Still pending, poll again
        if (attempts < maxAttempts) {
          setTimeout(poll, 10000);
        } else {
          setError('Video generation timed out. Please try again.');
          setStatus('error');
        }
      } catch (err: any) {
        setError('Failed to check video status');
        setStatus('error');
      }
    };

    poll();
  }, []);

  const handleDownload = () => {
    if (filename) {
      const link = document.createElement('a');
      link.href = getDownloadUrl(filename);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleUploadToDrive = async () => {
    if (!filename) return;
    setUploading(true);
    setUploadError('');
    setUploadResult(null);
    try {
      const result = await uploadToDrive(filename);
      setUploadResult(result);
    } catch (err: any) {
      setUploadError(
        err.response?.data?.detail || 'Failed to upload to Google Drive'
      );
    } finally {
      setUploading(false);
    }
  };

  const handlePublishArticle = async () => {
    if (!articleData) return;
    setPublishing(true);
    setError('');
    try {
      const result = await publishArticle(articleData.article_id);
      setPublishResult(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to publish article');
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="animate-fade-in">
      {/* Header with selection summary */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-brand-300 via-brand-400 to-accent-400 bg-clip-text text-transparent">
          Generate Media
        </h2>
        <p className="text-text-secondary mt-2">
          Creating misinformation scenario for <span className="text-brand-300 font-semibold">{target.name}</span>
          {' '}× <span className="text-accent-400 font-semibold">{narrative.title}</span>
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <div className="glass-card p-4">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">Target</div>
          <div className="text-text-primary font-semibold">{target.name}</div>
          <div className="text-text-secondary text-sm">{target.role}</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">Narrative</div>
          <div className="text-text-primary font-semibold">{narrative.icon} {narrative.title}</div>
          <div className="text-text-secondary text-sm">{narrative.description}</div>
        </div>
      </div>

      {/* Generation type toggle */}
      <div className="flex justify-center mb-6">
        <div className="inline-flex bg-surface-800 rounded-xl p-1 border border-surface-600">
          <button
            id="toggle-article"
            onClick={() => setGenType('article')}
            className={`px-6 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300 cursor-pointer ${genType === 'article'
              ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/25'
              : 'text-text-secondary hover:text-text-primary'
              }`}
          >
            📰 Article
          </button>
          <button
            id="toggle-video"
            onClick={() => setGenType('video')}
            className={`px-6 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300 cursor-pointer ${genType === 'video'
              ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/25'
              : 'text-text-secondary hover:text-text-primary'
              }`}
          >
            🎬 Video
          </button>
        </div>
      </div>

      {/* Prompt area */}
      <div className="glass-card p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <label className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
            AI-Generated Prompt {genType === 'article' && '(for reference)'}
          </label>
          {status !== 'generating-prompt' && (
            <button
              id="regenerate-prompt-btn"
              onClick={() => handleGeneratePrompt()}
              className="text-xs text-brand-400 hover:text-brand-300 transition-colors cursor-pointer font-medium"
            >
              ↻ Regenerate
            </button>
          )}
        </div>

        {status === 'generating-prompt' ? (
          <div className="flex items-center gap-3 py-8 justify-center">
            <div className="w-5 h-5 border-2 border-brand-400/30 border-t-brand-400 rounded-full animate-spin" />
            <span className="text-text-secondary text-sm">Gemini is crafting your prompt{genType === 'article' ? 's' : ''}...</span>
          </div>
        ) : genType === 'article' ? (
          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2 block">
                🖼️ Image Prompt
              </label>
              <textarea
                id="image-prompt-editor"
                value={imagePrompt}
                onChange={(e) => setImagePrompt(e.target.value)}
                rows={4}
                className="w-full bg-surface-900/50 text-text-primary border border-surface-600 rounded-xl px-4 py-3 text-sm leading-relaxed focus:outline-none focus:border-brand-400 focus:ring-1 focus:ring-brand-400/20 resize-y transition-colors"
                placeholder="Visual description for the article image..."
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2 block">
                📝 Article Content Prompt
              </label>
              <textarea
                id="article-prompt-editor"
                value={articlePrompt}
                onChange={(e) => setArticlePrompt(e.target.value)}
                rows={5}
                className="w-full bg-surface-900/50 text-text-primary border border-surface-600 rounded-xl px-4 py-3 text-sm leading-relaxed focus:outline-none focus:border-brand-400 focus:ring-1 focus:ring-brand-400/20 resize-y transition-colors"
                placeholder="Scenario description for article text generation..."
              />
            </div>
          </div>
        ) : (
          <textarea
            id="prompt-editor"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={5}
            className="w-full bg-surface-900/50 text-text-primary border border-surface-600 rounded-xl px-4 py-3 text-sm leading-relaxed focus:outline-none focus:border-brand-400 focus:ring-1 focus:ring-brand-400/20 resize-y transition-colors"
            placeholder="The AI-generated prompt will appear here..."
          />
        )}
        {genType === 'article' && (
          <p className="text-xs text-text-muted mt-2">
            💡 Both prompts describe the same story - one for the image, one for the article text.
          </p>
        )}
      </div>

      {/* Generate button */}
      {((status === 'prompt-ready' || status === 'error') && prompt && genType === 'video') && (
        <div className="flex justify-center mb-8">
          <button
            id="generate-media-btn"
            onClick={handleGenerate}
            className="group relative px-10 py-4 bg-gradient-to-r from-brand-500 to-brand-600 rounded-xl text-white font-bold text-base hover:from-brand-400 hover:to-brand-500 transition-all duration-300 shadow-[0_4px_24px_oklch(0.55_0.22_280/0.3)] hover:shadow-[0_8px_40px_oklch(0.55_0.22_280/0.5)] hover:scale-105 active:scale-95 cursor-pointer"
          >
            <span className="flex items-center gap-2">
              🎬 Generate Video
            </span>
          </button>
        </div>
      )}

      {/* Generate Article button - shown immediately for article type */}
      {genType === 'article' && (status === 'prompt-ready' || status === 'error') && imagePrompt && articlePrompt && (
        <div className="flex justify-center mb-8">
          <button
            id="generate-article-btn"
            onClick={handleGenerate}
            className="group relative px-10 py-4 bg-gradient-to-r from-brand-500 to-brand-600 rounded-xl text-white font-bold text-base hover:from-brand-400 hover:to-brand-500 transition-all duration-300 shadow-[0_4px_24px_oklch(0.55_0.22_280/0.3)] hover:shadow-[0_8px_40px_oklch(0.55_0.22_280/0.5)] hover:scale-105 active:scale-95 cursor-pointer"
          >
            <span className="flex items-center gap-2">
              📰 Generate Article with Image
            </span>
          </button>
        </div>
      )}

      {/* Loading state */}
      {(status === 'generating-media' || status === 'generating-article' || status === 'polling-video') && (
        <div className="glass-card p-8 mb-6 text-center animate-pulse-glow">
          <div className="flex flex-col items-center gap-4">
            <div className="w-16 h-16 border-4 border-brand-400/20 border-t-brand-400 rounded-full animate-spin" />
            <p className="text-text-primary font-semibold text-lg">
              {status === 'generating-media'
                ? 'Starting video generation...'
                : status === 'generating-article'
                  ? 'Generating article with image (this may take a moment)...'
                  : 'Generating video (this can take a few minutes)...'
              }
            </p>
            {status === 'polling-video' && (
              <div className="w-full max-w-xs">
                <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-brand-500 to-brand-400 rounded-full transition-all duration-1000"
                    style={{ width: `${pollingProgress}%` }}
                  />
                </div>
                <p className="text-text-muted text-xs mt-2">Polling for completion...</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error state */}
      {status === 'error' && error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-5 mb-6 animate-fade-in">
          <div className="flex items-start gap-3">
            <span className="text-red-400 text-xl mt-0.5">⚠️</span>
            <div>
              <p className="text-red-300 font-semibold text-sm">Generation Failed</p>
              <p className="text-red-400/80 text-sm mt-1">{error}</p>
              <p className="text-text-muted text-xs mt-2">
                This may be due to safety filters. Try modifying the prompt or selecting a different combination.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Result display - Articles */}
      {status === 'complete' && genType === 'article' && articleData && (
        <div className="glass-card p-6 mb-6 animate-slide-up">
          <h3 className="text-sm uppercase tracking-wider text-text-muted mb-4 font-semibold">Generated Article</h3>

          <div className="bg-surface-900 border border-surface-600 rounded-xl overflow-hidden mb-4">
            <iframe
              id="generated-article"
              src={getArticleUrl(articleData.article_url)}
              className="w-full h-[600px] border-0"
              title="Generated Article"
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <a
              href={getArticleUrl(articleData.article_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 rounded-xl text-white font-semibold text-sm transition-all duration-300 shadow-lg hover:shadow-blue-500/25 cursor-pointer"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              Open Article in New Tab
            </a>
            <button
              id="publish-article-btn"
              onClick={handlePublishArticle}
              disabled={publishing}
              className={`flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-white font-semibold text-sm transition-all duration-300 shadow-lg cursor-pointer ${publishing
                ? 'bg-accent-600/60 cursor-not-allowed'
                : 'bg-gradient-to-r from-accent-500 to-accent-600 hover:from-accent-400 hover:to-accent-500 hover:shadow-accent-500/25'
                }`}
            >
              {publishing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Publishing…
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  Publish Article
                </>
              )}
            </button>
          </div>

          {/* Publish success message */}
          {publishResult && (
            <div className="mt-4 bg-green-500/10 border border-green-500/30 rounded-xl p-4 animate-fade-in">
              <div className="flex items-start gap-3">
                <span className="text-green-400 text-lg">✅</span>
                <div className="flex-1">
                  <p className="text-green-300 font-semibold text-sm">Article Published</p>
                  <p className="text-text-muted text-xs mt-1">{publishResult.message}</p>
                  <a
                    href={publishResult.published_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-brand-400 hover:text-brand-300 text-xs mt-2 transition-colors"
                  >
                    View Published Article ↗
                  </a>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Result display - Image/Video */}
      {status === 'complete' && genType !== 'article' && mediaUrl && (
        <div className="glass-card p-6 mb-6 animate-slide-up">
          <h3 className="text-sm uppercase tracking-wider text-text-muted mb-4 font-semibold">Generated Result</h3>

          <div className="rounded-xl overflow-hidden border border-surface-600 mb-4 bg-surface-900">
            <video
              id="generated-result"
              src={mediaUrl}
              controls
              className="w-full max-h-[600px]"
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              id="download-btn"
              onClick={handleDownload}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 rounded-xl text-white font-semibold text-sm transition-all duration-300 shadow-lg hover:shadow-green-500/25 cursor-pointer"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download Video
            </button>
            <button
              id="upload-to-drive-btn"
              onClick={handleUploadToDrive}
              disabled={uploading}
              className={`flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-white font-semibold text-sm transition-all duration-300 shadow-lg cursor-pointer ${uploading
                ? 'bg-accent-600/60 cursor-not-allowed'
                : 'bg-gradient-to-r from-accent-500 to-accent-600 hover:from-accent-400 hover:to-accent-500 hover:shadow-accent-500/25'
                }`}
            >
              {uploading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Uploading…
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19.35 10.04A7.49 7.49 0 0012 4C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 000 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z" />
                  </svg>
                  Upload to Google Drive for Detection
                </>
              )}
            </button>
          </div>

          {/* Upload success message */}
          {uploadResult && (
            <div className="mt-4 bg-green-500/10 border border-green-500/30 rounded-xl p-4 animate-fade-in">
              <div className="flex items-start gap-3">
                <span className="text-green-400 text-lg">✅</span>
                <div>
                  <p className="text-green-300 font-semibold text-sm">Uploaded to Google Drive</p>
                  <p className="text-text-muted text-xs mt-1">
                    File is now available for the detection system.
                  </p>
                  {uploadResult.web_view_link && (
                    <a
                      href={uploadResult.web_view_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-brand-400 hover:text-brand-300 text-xs mt-2 transition-colors"
                    >
                      Open in Google Drive ↗
                    </a>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Upload error message */}
          {uploadError && (
            <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-xl p-4 animate-fade-in">
              <div className="flex items-start gap-3">
                <span className="text-red-400 text-lg">⚠️</span>
                <div>
                  <p className="text-red-300 font-semibold text-sm">Upload Failed</p>
                  <p className="text-red-400/80 text-xs mt-1">{uploadError}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Start over */}
      <div className="flex justify-center mt-6">
        <button
          id="start-over-btn"
          onClick={onReset}
          className="text-text-muted hover:text-text-secondary text-sm transition-colors cursor-pointer underline decoration-dotted underline-offset-4"
        >
          ← Start Over with Different Selection
        </button>
      </div>
    </div>
  );
}
