import { useEffect, useRef, useState } from 'react'
import { photos, type Photo } from './data/photos'

function PhotoImage({ photo, eager = false, viewer = false }: {
  photo: Photo; eager?: boolean; viewer?: boolean
}) {
  const [status, setStatus] = useState<'loading' | 'loaded' | 'failed'>('loading')
  return (
    <span className={`photo-image ${viewer ? 'viewer-image' : ''}`} data-status={status}>
      {status === 'failed' ? (
        <span className="image-message" role="status">Photo unavailable<span>{photo.alt}</span></span>
      ) : (
        <>
          {status === 'loading' && <span className="image-message">Loading photo…</span>}
          <img src={photo.src} alt={photo.alt} width={photo.width} height={photo.height}
            loading={eager ? 'eager' : 'lazy'} decoding="async"
            onLoad={() => setStatus('loaded')} onError={() => setStatus('failed')} />
        </>
      )}
    </span>
  )
}

function PhotoViewer({ initialIndex, onClose }: { initialIndex: number; onClose: () => void }) {
  const [index, setIndex] = useState(initialIndex)
  const dialogRef = useRef<HTMLDialogElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const photo = photos[index]

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
    setIndex((current) => (current + direction + photos.length) % photos.length)
  }

  return (
    <dialog ref={dialogRef} className="viewer" aria-label="Photo viewer"
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
        <span>Selected photographs</span>
        <button ref={closeRef} onClick={onClose} aria-label="Close photo viewer">Close <span aria-hidden="true">×</span></button>
      </div>
      <PhotoImage key={photo.src} photo={photo} eager viewer />
      <div className="viewer-toolbar">
        <button onClick={() => navigate(-1)} disabled={photos.length < 2} aria-label="Previous photo">Previous</button>
        <p role="status" aria-atomic="true"><span>{index + 1} / {photos.length}</span><span className="viewer-caption">{photo.alt}</span></p>
        <button onClick={() => navigate(1)} disabled={photos.length < 2} aria-label="Next photo">Next</button>
      </div>
    </dialog>
  )
}

export default function App() {
  const [activeIndex, setActiveIndex] = useState<number | null>(null)
  return (
    <>
      <header className="site-header">
        <h1>Mihajlo Mandušić</h1>
        <nav className="contact-links" aria-label="Contact">
          <a href="https://www.instagram.com/mihajlo.mandusic/">Instagram</a>
          <a href="mailto:mixoidm@gmail.com">Mail</a>
        </nav>
      </header>
      <main id="gallery">
        {photos.length === 0 ? (
          <div className="empty-gallery"><h2>No photographs yet</h2><p>New photographs will appear here.</p></div>
        ) : (
          <ul className="gallery" aria-label="Selected photographs">
            {photos.map((photo, index) => (
              <li key={photo.src}>
                <button className="photo-button" aria-label={`Open photo ${index + 1}: ${photo.alt}`}
                  onClick={(event) => { event.currentTarget.focus(); setActiveIndex(index) }}>
                  <PhotoImage photo={photo} eager={index < 2} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </main>
      <footer className="site-footer">A collection of personal & travel photographs.</footer>
      {activeIndex !== null && <PhotoViewer initialIndex={activeIndex} onClose={() => setActiveIndex(null)} />}
    </>
  )
}
