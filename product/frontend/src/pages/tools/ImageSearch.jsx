import { useState, useRef } from 'react';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import api from '../../services/api';
import {
  PhotoIcon,
  ArrowTopRightOnSquareIcon,
  MagnifyingGlassCircleIcon,
  ArrowUpTrayIcon,
  LinkIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';

const ENGINE_LABELS = {
  google: 'Google Lens',
  yandex: 'Yandex',
  tineye: 'TinEye',
  bing: 'Bing',
};

export default function ImageSearch() {
  const [mode, setMode] = useState('url');
  const [imageUrl, setImageUrl] = useState('');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    setResult(null);

    try {
      if (mode === 'url') {
        const trimmed = imageUrl.trim();
        if (!trimmed) { setError('Entrez une URL d\'image'); setLoading(false); return; }
        const body = await api.post('/image-search/reverse', { domain: trimmed });
        setResult({
          success: body.success,
          data: body.data,
          summary: body.summary,
          error: body.error,
        });
      } else {
        if (!file) { setError('Sélectionnez une image'); setLoading(false); return; }
        const form = new FormData();
        form.append('file', file);
        const res = await api.post('/image-search/analyze', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 30000,
        });
        setResult({
          success: res.success,
          data: res.data,
          summary: res.summary,
          error: res.error,
        });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      setPreview(URL.createObjectURL(f));
      setError('');
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-pink-500/10 border border-pink-500/20">
          <MagnifyingGlassCircleIcon className="w-6 h-6 text-pink-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Image Search</h1>
          <p className="text-sm text-gray-500">Recherche inversée et analyse d'image (EXIF, métadonnées, hash)</p>
        </div>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => { setMode('url'); setFile(null); setPreview(null); setError(''); setResult(null); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                mode === 'url'
                  ? 'bg-pink-500/10 text-pink-400 border border-pink-500/20'
                  : 'bg-gray-800 text-gray-500 hover:text-gray-300 border border-transparent'
              }`}
            >
              <LinkIcon className="w-4 h-4" />
              URL
            </button>
            <button
              type="button"
              onClick={() => { setMode('file'); setImageUrl(''); setError(''); setResult(null); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                mode === 'file'
                  ? 'bg-pink-500/10 text-pink-400 border border-pink-500/20'
                  : 'bg-gray-800 text-gray-500 hover:text-gray-300 border border-transparent'
              }`}
            >
              <ArrowUpTrayIcon className="w-4 h-4" />
              Fichier
            </button>
          </div>

          {mode === 'url' ? (
            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
                URL de l'image
              </label>
              <input
                type="url"
                value={imageUrl}
                onChange={(e) => { setImageUrl(e.target.value); setError(''); }}
                className="input-soc text-base"
                placeholder="https://example.com/image.jpg"
                autoFocus
              />
            </div>
          ) : (
            <div className="space-y-3">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
                Image
              </label>
              <div
                onClick={() => fileRef.current?.click()}
                className="border-2 border-dashed border-gray-700 rounded-lg p-8 text-center cursor-pointer hover:border-pink-500/50 transition-colors"
              >
                {preview ? (
                  <img src={preview} alt="Preview" className="max-h-48 mx-auto rounded" />
                ) : (
                  <div className="text-gray-500">
                    <PhotoIcon className="w-12 h-12 mx-auto mb-2" />
                    <p className="text-sm">Cliquez pour sélectionner une image</p>
                    <p className="text-xs mt-1">PNG, JPG, GIF, WebP, BMP</p>
                  </div>
                )}
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/png,image/jpeg,image/gif,image/webp,image/bmp"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>
              {file && (
                <p className="text-xs text-gray-500">{file.name} · {(file.size / 1024).toFixed(1)} KB</p>
              )}
            </div>
          )}

          {error && <p className="text-xs text-red-400">{error}</p>}
          <Button type="submit" size="lg" loading={loading} className="w-full sm:w-auto">
            {loading ? 'Analyse...' : mode === 'url' ? 'Rechercher sur les moteurs' : 'Analyser l\'image'}
          </Button>
        </form>
      </Card>

      {result && result.success && result.data && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Résultats</h3>

          {/* Summary */}
          {result.summary && <p className="text-xs text-gray-400 mb-4">{result.summary}</p>}

          {/* Uploaded image preview + info */}
          {result.data.source === 'upload' && (
            <div className="space-y-4 mb-4">
              {result.data.temp_url && (
                <img
                  src={`http://localhost:8000${result.data.temp_url}`}
                  alt="Uploaded"
                  className="max-h-48 rounded border border-gray-700"
                />
              )}

              {/* EXIF / Image info */}
              {result.data.exif && (
                <div className="bg-gray-900/50 rounded-lg p-3 space-y-1 text-xs font-mono">
                  {result.data.exif.format && (
                    <p className="text-gray-400">Format: <span className="text-emerald-400">{result.data.exif.format} {result.data.exif.width}x{result.data.exif.height}</span></p>
                  )}
                  {result.data.exif.exif?.DateTimeOriginal && (
                    <p className="text-gray-400">Date: <span className="text-emerald-400">{result.data.exif.exif.DateTimeOriginal}</span></p>
                  )}
                  {result.data.exif.exif?.Make && (
                    <p className="text-gray-400">Appareil: <span className="text-emerald-400">{result.data.exif.Make} {result.data.exif.Model}</span></p>
                  )}
                  {result.data.exif.gps && (
                    <p className="text-gray-400">GPS: <span className="text-emerald-400">{result.data.exif.gps.latitude}, {result.data.exif.gps.longitude}</span></p>
                  )}
                </div>
              )}

              {/* Hashes */}
              {result.data.hashes && (
                <div className="bg-gray-900/50 rounded-lg p-3 space-y-1 text-xs font-mono">
                  <p className="text-gray-400">MD5: <span className="text-cyan-400">{result.data.hashes.md5}</span></p>
                  <p className="text-gray-400">SHA1: <span className="text-cyan-400">{result.data.hashes.sha1}</span></p>
                  <p className="text-gray-400">SHA256: <span className="text-cyan-400">{result.data.hashes.sha256}</span></p>
                </div>
              )}
            </div>
          )}

          {/* URL metadata */}
          {result.data.metadata?.content_type && (
            <div className="flex items-center gap-2 mb-4 text-xs text-gray-500">
              <PhotoIcon className="w-4 h-4" />
              <span>{result.data.metadata.content_type}</span>
              {result.data.metadata.size && <span>· {Math.round(result.data.metadata.size / 1024)} KB</span>}
            </div>
          )}

          {/* Search links */}
          {result.data.search_links && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Recherche inversée</p>
              {result.data.search_links.note && (
                <p className="text-xs text-amber-400">{result.data.search_links.note}</p>
              )}
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(result.data.search_links)
                  .filter(([k]) => k !== 'note')
                  .map(([engine, url]) => (
                    <a
                      key={engine}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50 border border-gray-700/50 hover:border-pink-500/30 transition-all group"
                    >
                      <span className="text-sm text-gray-300 group-hover:text-pink-400 transition-colors">
                        {ENGINE_LABELS[engine] || engine}
                      </span>
                      <ArrowTopRightOnSquareIcon className="w-4 h-4 text-gray-600 group-hover:text-pink-400" />
                    </a>
                  ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {result && !result.success && (
        <Card><p className="text-sm text-red-400">{result.error || 'Erreur'}</p></Card>
      )}
    </div>
  );
}
