import { useEffect, useRef, useState } from 'react'
import { albums, type Album, type PhotoVariant } from './data/albums'

function PhotoImage({ variant, alt, eager = false, viewer = false }: {
  variant: PhotoVariant; alt: string; eager?: boolean; viewer?: boolean
}) {
  const [status, setStatus] = useState<'loading' | 'loaded' | 'failed'>('loading')
  return (
    <span className={`photo-image ${viewer ? 'viewer-image' : ''}`} data-status={status}>
      {status === 'failed' ? (
        <span className="image-message" role="status">Photo unavailable<span>{alt}</span></span>
      ) : (
        <>
          {status === 'loading' && <span className="image-message">Loading photo…</span>}
          <img src={variant.src} alt={alt} width={variant.width} height={variant.height}
            loading={eager ? 'eager' : 'lazy'} decoding="async"
            onLoad={() => setStatus('loaded')} onError={() => setStatus('failed')} />
        </>
      )}
    </span>
  )
}

function PhotoViewer({ album, onClose }: { album: Album; onClose: () => void }) {
  const [index, setIndex] = useState(0)
  const dialogRef = useRef<HTMLDialogElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const thumbnailRef = useRef<HTMLDivElement>(null)
  const focusSelectedThumbnail = useRef(false)
  const photos = album.photos
  const photo = photos[index]
  const windowStart = Math.max(0, Math.min(index - 2, photos.length - 5))
  const nearbyPhotos = photos.slice(windowStart, windowStart + 5)

  useEffect(() => {
    // Arrow navigation can remove the focused thumbnail from the nearby window.
    if (focusSelectedThumbnail.current) {
      thumbnailRef.current?.querySelector<HTMLButtonElement>('[aria-current="true"]')?.focus()
      focusSelectedThumbnail.current = false
    }
  }, [index])

  useEffect(() => {
    const dialog = dialogRef.current!
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const scrollY = window.scrollY
    const oldStyles = {
      position: document.body.style.position, top: document.body.style.top,
      width: document.body.style.width, overflow: document.body.style.overflow,
    }
    // A fixed body also prevents background scrolling in mobile browsers.
    Object.assign(document.body.style, { position: 'fixed', top: `-${scrollY}px`, width: '100%', overflow: 'hidden' })
    dialog.showModal()
    closeRef.current?.focus()
    return () => {
      dialog.close()
      Object.assign(document.body.style, oldStyles)
      window.scrollTo(0, scrollY)
      trigger?.focus({ preventScroll: true })
    }
  }, [])

  function navigate(direction: number) {
    focusSelectedThumbnail.current = thumbnailRef.current?.contains(document.activeElement) ?? false
    setIndex((current) => (current + direction + photos.length) % photos.length)
  }

  return (
    <dialog ref={dialogRef} className="viewer" aria-label={`${album.title} photo viewer`}
      onCancel={(event) => { event.preventDefault(); onClose() }}
      onKeyDown={(event) => {
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
          event.preventDefault()
          navigate(event.key === 'ArrowLeft' ? -1 : 1)
        }
        // Cycle through controls at both ends of the modal's tab order.
        if (event.key === 'Tab') {
          const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not(:disabled)'))
          const first = buttons[0]
          const last = buttons[buttons.length - 1]
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault(); last.focus()
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault(); first.focus()
          }
        }
      }}>
      <div className="viewer-topbar">
        <span>{album.title}</span>
        <button ref={closeRef} onClick={onClose} aria-label="Close photo viewer">Close <span aria-hidden="true">×</span></button>
      </div>
      <div className="viewer-content">
        <PhotoImage key={photo.viewer.src} variant={photo.viewer} alt={photo.alt} eager viewer />
        <div ref={thumbnailRef} className="viewer-thumbnails" role="group" aria-label="Nearby photos">
          {nearbyPhotos.map((nearbyPhoto, offset) => {
            const photoIndex = windowStart + offset
            return (
              <button key={nearbyPhoto.id} className="thumbnail-button"
                aria-label={`View photo ${photoIndex + 1} of ${photos.length}: ${nearbyPhoto.alt}`}
                aria-current={photoIndex === index ? 'true' : undefined}
                onClick={() => setIndex(photoIndex)}>
                <PhotoImage key={nearbyPhoto.thumbnail.src} variant={nearbyPhoto.thumbnail} alt={nearbyPhoto.alt} eager />
              </button>
            )
          })}
        </div>
      </div>
      <div className="viewer-toolbar">
        <button onClick={() => navigate(-1)} disabled={photos.length < 2} aria-label="Previous photo">Previous</button>
        <p role="status" aria-atomic="true"><span>{index + 1} / {photos.length}</span><span className="viewer-caption">{photo.alt}</span></p>
        <button onClick={() => navigate(1)} disabled={photos.length < 2} aria-label="Next photo">Next</button>
      </div>
    </dialog>
  )
}

export default function App() {
  const [activeAlbumId, setActiveAlbumId] = useState<string | null>(null)
  const visibleAlbums = albums.filter((album) => album.photos.length > 0)
  const activeAlbum = visibleAlbums.find((album) => album.id === activeAlbumId)
  return (
    <>
      <header className="site-header">
        <h1>Mihajlo Mandušić</h1>
        <nav className="contact-links" aria-label="Contact">
          <a href="https://www.instagram.com/mihajlo.mandusic/" aria-label="Instagram" title="Instagram">
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <rect x="3" y="3" width="18" height="18" rx="5" />
              <circle cx="12" cy="12" r="4" />
              <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
            </svg>
          </a>
          <a href="mailto:mixoidm@gmail.com" aria-label="Email Mihajlo Mandušić" title="Email Mihajlo Mandušić">
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="m3 6 9 7 9-7" />
            </svg>
          </a>
        </nav>
      </header>
      <main id="gallery">
        {visibleAlbums.length === 0 ? (
          <div className="empty-gallery"><h2>No albums yet</h2><p>New photo series will appear here.</p></div>
        ) : (
          <ul className="gallery" aria-label="Photo albums">
            {visibleAlbums.map((album, index) => (
              <li key={album.id}>
                <button className="photo-button" aria-label={`Open album: ${album.title}`} aria-haspopup="dialog"
                  onClick={(event) => { event.currentTarget.focus(); setActiveAlbumId(album.id) }}>
                  <PhotoImage key={album.photos[0].preview.src} variant={album.photos[0].preview} alt={album.photos[0].alt} eager={index < 3} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </main>
      <footer className="site-footer">© Mihajlo Mandušić 2027</footer>
      {activeAlbum && <PhotoViewer key={activeAlbum.id} album={activeAlbum} onClose={() => setActiveAlbumId(null)} />}
    </>
  )
}
