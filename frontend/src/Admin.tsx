import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { Album } from './albums'
import './admin.css'

type Selection = { file: File; url: string; id: string }
class ApiError extends Error {
  status: number
  constructor(message: string, status: number) { super(message); this.status = status }
}

async function api(url: string, options?: RequestInit) {
  const response = await fetch(url, options)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status}). Please retry.`, response.status)
  }
  return response.json()
}

function moved<T>(items: T[], from: number, to: number): T[] {
  const result = [...items]
  const [item] = result.splice(from, 1)
  result.splice(to, 0, item)
  return result
}

function Cover({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false)
  return <div className="admin-cover">{failed ? <span>Preview unavailable</span> :
    <img src={src} alt={alt} onError={() => setFailed(true)} />}</div>
}

function CreateAlbum({ onCreated, onCancel }: { onCreated: () => Promise<void>; onCancel: () => void }) {
  const [title, setTitle] = useState('')
  const [photos, setPhotos] = useState<Selection[]>([])
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [uncertain, setUncertain] = useState(false)
  const requestId = useRef(crypto.randomUUID())
  const urls = useRef<string[]>([])
  const submitting = useRef(false)
  const titleInput = useRef<HTMLInputElement>(null)
  useEffect(() => {
    titleInput.current?.focus()
    return () => urls.current.forEach(URL.revokeObjectURL)
  }, [])

  function select(files: FileList | null) {
    if (!files) return
    const chosen = Array.from(files)
    if (!chosen.length || chosen.length > 30 || chosen.some(file => file.size > 20 * 1024 * 1024) || chosen.reduce((sum, file) => sum + file.size, 0) > 100 * 1024 * 1024) {
      setError('Choose 1–30 JPEG photos, at most 20 MiB each and 100 MiB total.')
      return
    }
    urls.current.forEach(URL.revokeObjectURL)
    const selection = chosen.map(file => ({ file, url: URL.createObjectURL(file), id: crypto.randomUUID() }))
    urls.current = selection.map(photo => photo.url)
    setPhotos(selection)
    setError('')
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (submitting.current) return
    if (!title.trim() || !photos.length) { setError('Enter a title and choose at least one JPEG photo.'); return }
    submitting.current = true
    setPending(true)
    setError('')
    const form = new FormData()
    form.append('title', title.trim())
    form.append('request_id', requestId.current)
    photos.forEach(photo => form.append('photos', photo.file))
    try {
      await api('/api/admin/albums', { method: 'POST', body: form })
    } catch (failure) {
      const knownRejection = failure instanceof ApiError && failure.status >= 400 && failure.status < 500
      setUncertain(!knownRejection)
      if (knownRejection) requestId.current = crypto.randomUUID()
      setError(knownRejection ? (failure as Error).message : 'The result could not be confirmed. Keep this page open and retry the same creation to check or finish it without creating a duplicate.')
      submitting.current = false
      setPending(false)
      return
    }
    await onCreated()
  }

  return <section aria-labelledby="create-title" className="admin-panel">
    <h2 id="create-title">Add album</h2>
    <p>The first photo is the cover and opening image. After creation, changes require deleting and recreating the album.</p>
    <form onSubmit={submit} aria-busy={pending}>
      <fieldset disabled={pending || uncertain}>
        <label htmlFor="album-title">Album title</label>
        <input ref={titleInput} id="album-title" required maxLength={120} value={title} onChange={event => setTitle(event.target.value)} />
        <label htmlFor="album-photos">{photos.length ? 'Choose photos again (replaces selection)' : 'Choose photos'}</label>
        <p id="upload-limits">JPEG only. 1–30 photos, up to 20 MiB each, 100 MiB total, and 40 million pixels per photo.</p>
        <input id="album-photos" type="file" accept="image/jpeg,.jpg,.jpeg" multiple aria-describedby="upload-limits" onChange={event => { select(event.target.files); event.target.value = '' }} />
        <ol className="admin-list">
          {photos.map((photo, index) => <li key={photo.id} className="admin-row">
            <Cover src={photo.url} alt={`Selected photo ${index + 1}`} />
            <div className="admin-details"><strong>{index + 1}. {photo.file.name}</strong><p>{index === 0 ? 'Cover · opens first' : `Photo ${index + 1}`}</p></div>
            <div className="admin-actions">
              <button type="button" disabled={index === 0} aria-label={`Move photo ${index + 1} earlier`} onClick={() => setPhotos(moved(photos, index, index - 1))}>Move earlier</button>
              <button type="button" disabled={index === photos.length - 1} aria-label={`Move photo ${index + 1} later`} onClick={() => setPhotos(moved(photos, index, index + 1))}>Move later</button>
            </div>
          </li>)}
        </ol>
      </fieldset>
      {error && <p role="alert" className="admin-error">{error}</p>}
      <p role="status">{pending ? 'Uploading and preparing photos… Keep this page open.' : uncertain ? 'The selection is locked until the result is confirmed.' : ''}</p>
      <div className="admin-actions">
        <button disabled={pending} type="submit">{pending ? 'Creating…' : uncertain ? 'Retry same creation' : 'Create album'}</button>
        <button disabled={pending || uncertain} type="button" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  </section>
}

function DeleteConfirmation({ album, onCancel, onConfirm }: { album: Album; onCancel: () => void; onConfirm: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => { dialog.current?.showModal() }, [])
  return <dialog ref={dialog} className="admin-confirm" aria-labelledby="delete-title" onCancel={event => { event.preventDefault(); onCancel() }}>
    <h2 id="delete-title">Delete “{album.title}”?</h2>
    <p>This permanently removes the album and its {album.photos.length} photos from the gallery. Original files on your computer are kept.</p>
    <div className="admin-actions"><button autoFocus onClick={onCancel}>Cancel</button><button onClick={onConfirm}>Delete album</button></div>
  </dialog>
}

export default function Admin() {
  const [albums, setAlbums] = useState<Album[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [adding, setAdding] = useState(false)
  const [pending, setPending] = useState(false)
  const [deleting, setDeleting] = useState<Album | null>(null)
  const [cleanup, setCleanup] = useState<string | null>(null)
  const mutation = useRef(false)
  const addButton = useRef<HTMLButtonElement>(null)
  const deleteButton = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    api('/api/albums', { signal: controller.signal }).then(setAlbums).catch(failure => {
      if (!controller.signal.aborted) setError(failure.message)
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [])

  async function refresh() {
    setLoading(true)
    setError('')
    try { setAlbums(await api('/api/albums')) }
    catch { setAlbums(null); setError('Could not load the saved album list. Check the backend and retry.') }
    finally { setLoading(false) }
  }

  async function mutate(action: () => Promise<{ message?: string; cleanup_pending?: number }>, albumId?: string) {
    if (mutation.current) return
    mutation.current = true
    setPending(true)
    setError('')
    setNotice('')
    try {
      const result = await action()
      setNotice(result.message ?? 'Album order saved.')
      if (albumId) setCleanup(result.cleanup_pending ? albumId : null)
    } catch (failure) {
      setNotice(failure instanceof Error ? `${failure.message} Reloaded the saved list; check the result before retrying.` : 'Could not confirm the change.')
      if (albumId) setCleanup(albumId)
    }
    await refresh()
    setPending(false)
    mutation.current = false
  }

  function move(index: number, direction: number) {
    if (!albums) return
    const ids = moved(albums, index, index + direction).map(album => album.id)
    void mutate(() => api('/api/admin/albums/order', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids, previous: albums.map(album => album.id) }) }))
  }

  function cancelDelete() {
    setDeleting(null)
    requestAnimationFrame(() => deleteButton.current?.focus())
  }

  function closeForm() { setAdding(false); requestAnimationFrame(() => addButton.current?.focus()) }
  const disabled = pending || loading || albums === null || cleanup !== null
  return <main className="admin">
    <header className="admin-header"><div><h1>Albums</h1><p>Local gallery management</p></div><a href="/">View gallery</a></header>
    <p>Create a complete album, move it in the gallery, or delete it. Albums are visible as soon as creation finishes.</p>
    <button ref={addButton} disabled={disabled || adding} onClick={() => { setAdding(true); setNotice('') }}>Add album</button>
    <p role="status">{pending ? 'Saving…' : notice}</p>
    {cleanup && <button disabled={pending || loading} onClick={() => void mutate(() => api(`/api/admin/albums/${encodeURIComponent(cleanup)}`, { method: 'DELETE' }), cleanup)}>Retry deletion / file cleanup</button>}
    {adding && <CreateAlbum onCancel={closeForm} onCreated={async () => { setNotice('Album created and added to the gallery.'); await refresh(); closeForm() }} />}
    {loading && <p role="status">Loading albums…</p>}
    {error && <div role="alert" className="admin-error"><p>{error}</p><button disabled={loading || pending} onClick={() => void refresh()}>Retry album list</button></div>}
    {!adding && albums && !loading && <section aria-label="Saved albums">
      {!albums.length && <p>No albums yet. Add an album to start your gallery.</p>}
      <ol className="admin-list">{albums.map((album, index) => <li key={album.id} className="admin-row">
        {album.photos[0] ? <Cover src={album.photos[0].thumbnail.src} alt="" /> : <div className="admin-cover">No cover</div>}
        <div className="admin-details"><h2>{album.title}</h2><p>{album.photos.length} {album.photos.length === 1 ? 'photo' : 'photos'}</p></div>
        <div className="admin-actions">
          <button disabled={disabled || index === 0} aria-label={`Move ${album.title} up`} onClick={() => move(index, -1)}>Move up</button>
          <button disabled={disabled || index === albums.length - 1} aria-label={`Move ${album.title} down`} onClick={() => move(index, 1)}>Move down</button>
          <button disabled={disabled} aria-label={`Delete ${album.title}`} onClick={event => { deleteButton.current = event.currentTarget; setDeleting(album) }}>Delete</button>
        </div>
      </li>)}</ol>
    </section>}
    {deleting && <DeleteConfirmation album={deleting} onCancel={cancelDelete} onConfirm={() => {
      const id = deleting.id
      setDeleting(null)
      void mutate(() => api(`/api/admin/albums/${encodeURIComponent(id)}`, { method: 'DELETE' }), id).then(() => addButton.current?.focus())
    }} />}
  </main>
}
