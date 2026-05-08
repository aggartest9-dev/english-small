import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getDirectDriveUrl(url: string | null | undefined): string {
  if (!url) return '';
  
  // Clean the URL
  const cleanUrl = url.trim();

  // Try to extract ID from various patterns
  let id = '';
  // Support /file/d/ID/view, /file/d/ID/edit, /file/d/ID
  const fileIdMatch = cleanUrl.match(/\/file\/d\/([a-zA-Z0-9_-]{25,})/);
  // Support ?id=ID or &id=ID or id=ID
  const idParamMatch = cleanUrl.match(/[?&]id=([a-zA-Z0-9_-]{25,})/);
  // Support /uc?id=ID
  const ucMatch = cleanUrl.match(/\/uc\?id=([a-zA-Z0-9_-]{25,})/);
  // Support folders/ID/
  const foldersMatch = cleanUrl.match(/\/folders\/([a-zA-Z0-9_-]{25,})/);
  
  if (fileIdMatch) {
    id = fileIdMatch[1];
  } else if (idParamMatch) {
    id = idParamMatch[1];
  } else if (ucMatch) {
    id = ucMatch[1];
  } else if (foldersMatch) {
    id = foldersMatch[1];
  } else {
    // Fallback search for any string that looks like a drive ID (usually 28-35 characters)
    const generalIdMatch = cleanUrl.match(/[a-zA-Z0-9_-]{28,40}/);
    if (generalIdMatch) id = generalIdMatch[0];
  }

  if (id && (cleanUrl.includes('drive.google.com') || cleanUrl.includes('docs.google.com') || cleanUrl.includes('google.com'))) {
    // drive.google.com/uc?export=download&id= is the user-requested format for direct media access
    return `https://drive.google.com/uc?export=download&id=${id}`;
  }

  return cleanUrl;
}
