import { FileObject } from "@ctypes/files";

export async function getFileContent(
  absoluteFilePath: string,
): Promise<string> {
  // const fileObject: { file_path: string; content: string } = await invoke(
  //   "request_file",
  //   { filePath: absoluteFilePath },
  // );
  // console.log("Got file content", fileObject);
  // return fileObject.content;
  return "";
}

export async function getAllFiles(repoPath: string): Promise<FileObject[]> {
  // const files: { file_path: string; content: string }[] = await invoke(
  //   "request_all_files",
  //   { repoPath },
  // );
  // const fileObjects: FileObject[] = files.map((file) => ({
  //   filePath: file.file_path,
  //   content: file.content,
  // }));
  // return fileObjects;
  return [];
}

export async function getAllFilePaths(repoPath: string) {
  // const filePaths: string[] = await invoke("request_all_file_paths", {
  //   repoPath,
  // });
  // return filePaths;
  return [];
}

export async function createFile(absoluteFilePath: string, content: string) {
  // console.log("Creating file", absoluteFilePath);
  // await invoke("perform_modification", {
  //   changeType: "create_file",
  //   fullPath: absoluteFilePath,
  //   content,
  // });
}

export async function editFile(absoluteFilePath: string, content: string) {
  // console.log("Editing file", absoluteFilePath);
  // await invoke("perform_modification", {
  //   changeType: "edit_file",
  //   fullPath: absoluteFilePath,
  //   content,
  // });
}
