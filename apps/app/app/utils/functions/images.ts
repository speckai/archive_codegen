import { LocalImage } from "@ctypes/image";
import { v4 as uuidv4 } from "uuid";

export const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

export interface ImageValidationResult {
  isValid: boolean;
  error?: string;
}

export function validateImageFile(file: File): ImageValidationResult {
  if (file.size > MAX_FILE_SIZE) {
    return {
      isValid: false,
      error: "Maximum file size is 5MB",
    };
  }
  return { isValid: true };
}

export function checkDuplicateImage(
  file: File,
  existingImages: LocalImage[],
): boolean {
  return existingImages.some((img) => img.name === file.name);
}

export function createImageFromFile(file: File): Promise<LocalImage> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const newImage: LocalImage = {
        id: uuidv4(),
        file,
        previewUrl: reader.result as string,
        name: file.name || `Image ${new Date().toISOString()}`,
        size: file.size,
        type: file.type,
      };
      resolve(newImage);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export async function handleImageFile(
  file: File,
  existingImages: LocalImage[],
): Promise<{ image?: LocalImage; error?: string }> {
  const validation = validateImageFile(file);
  if (!validation.isValid) {
    return { error: validation.error };
  }

  if (checkDuplicateImage(file, existingImages)) {
    return { error: `${file.name} has already been added` };
  }

  try {
    const image = await createImageFromFile(file);
    return { image };
  } catch (error) {
    return { error: "Failed to process image" };
  }
}

export function formatFileSize(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(2)}MB`;
}
