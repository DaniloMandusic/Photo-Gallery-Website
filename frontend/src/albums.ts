export type PhotoVariant = {
  src: string
  width: number
  height: number
}

export type AlbumPhoto = {
  id: string
  alt: string
  thumbnail: PhotoVariant
  preview: PhotoVariant
  viewer: PhotoVariant
}

export type Album = {
  id: string
  title: string
  photos: AlbumPhoto[]
}
