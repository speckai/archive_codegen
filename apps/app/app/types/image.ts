export interface LocalImage {
  id: string;
  file: File;
  previewUrl: string;
  name: string;
  size: number;
  type: string;
}

export interface Image {
  id: string;
  name: string;
  previewUrl: string;
  type: string;
}

export const convertFromApi = (apiImage: any): Image => {
  return {
    id: apiImage.size,
    name: apiImage.name,
    previewUrl: apiImage.data,
    type: apiImage.type,
  };
};

export interface UrlScreenshotMetadata {
  imageId: string;
  annotation: string;
}
