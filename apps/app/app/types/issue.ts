export interface Issue {
  content: string;
  assetUrls: { [key: string]: any };
  textModels: { [key: string]: any };
  referencedFiles: string[];
}
