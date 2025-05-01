interface SelectedComponent {
  componentName: string;
  fileName: string;
  filePath: string;
  lineNumber: number;
  changeMessage: string;
  htmlTag?: string;
  htmlClassName?: string;
  htmlChildren?: string;
  noComponentInfo?: boolean;
  parents?: Array<{
    htmlTag: string;
    htmlClassName: string;
    htmlChildren: string;
  }>;
}

const convertFromApi = (apiSelectedComponent: any): SelectedComponent => {
  return {
    componentName: apiSelectedComponent.name,
    fileName: apiSelectedComponent.file_path.split("/").pop(),
    filePath: apiSelectedComponent.file_path,
    lineNumber: apiSelectedComponent.line_number,
    changeMessage: apiSelectedComponent.change_message,
    htmlTag: apiSelectedComponent.html_tag || undefined,
    htmlClassName: apiSelectedComponent.html_class_name || undefined,
    htmlChildren: apiSelectedComponent.html_children || undefined,
    noComponentInfo: apiSelectedComponent.no_component_info,
    parents: apiSelectedComponent.parents || [],
  };
};

export { convertFromApi };
export type { SelectedComponent };
