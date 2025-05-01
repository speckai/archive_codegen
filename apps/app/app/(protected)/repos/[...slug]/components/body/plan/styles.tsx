export const customStyles = `
  .mdx-editor {
    --mdx-editor-text: #ffffff;
    --mdx-editor-bg: transparent;
    --mdx-editor-border: transparent;
    --mdx-editor-toolbar-bg: transparent;
    --mdx-editor-toolbar-border: transparent;
    --mdx-editor-resizer: transparent;
    --mdx-editor-resizer-hover: transparent;
    --mdx-editor-font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }

  .mdx-editor .prose {
    max-width: none;
    width: 100%;
    padding: 0;
    color: #ffffff;
  }

  .mdx-editor .prose p {
    margin-bottom: 1em;
    color: #ffffff;
  }

  .mdx-editor .prose h1 {
    margin-top: 1em;
    margin-bottom: 0.75em;
    font-weight: 700;
    font-size: 2em;
    color: #63b3ed;
  }

  .mdx-editor .prose h2 {
    margin-top: 1em;
    margin-bottom: 0.5em;
    font-weight: 600;
    font-size: 1.5em;
    color: #ffffff;
  }

  .mdx-editor .prose h3,
  .mdx-editor .prose h4,
  .mdx-editor .prose h5,
  .mdx-editor .prose h6 {
    margin-top: 1em;
    margin-bottom: 0.5em;
    font-weight: 600;
    color: #ffffff;
  }

  .mdx-editor .prose h3 { font-size: 1.25em; }
  .mdx-editor .prose h4 { font-size: 1.1em; }
  .mdx-editor .prose h5 { font-size: 1em; }
  .mdx-editor .prose h6 { font-size: 0.9em; }

  .mdx-editor .prose code {
    background-color: rgba(255, 255, 255, 0.1);
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: monospace;
    color: #000000;
  }

  .mdx-editor .prose pre {
    background-color: rgba(255, 255, 255, 0.1);
    padding: 1em;
    border-radius: 5px;
    overflow-x: auto;
    margin: 1em 0;
    color: #000000;
  }

  .mdx-editor .prose blockquote {
    border-left: 4px solid rgba(255, 255, 255, 0.3);
    padding-left: 1em;
    font-style: italic;
    margin: 1em 0;
    color: #ffffff;
  }

  .mdx-editor .prose ul,
  .mdx-editor .prose ol {
    padding-left: 1.5em;
    margin: 1em 0;
    color: #ffffff;
  }
  
  /* Hide the toolbar */
  .mdx-editor .mdx-editor-toolbar {
    display: none;
  }

  .description-markdown {
    color: #a0aec0;
    font-size: 0.875rem;
  }

  .description-markdown p {
    margin: 0;
  }

  .description-markdown code {
    background-color: rgba(255, 255, 255, 0.1);
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: monospace;
  }

  .description-markdown a {
    color: #63b3ed;
    text-decoration: none;
  }

  .description-markdown a:hover {
    text-decoration: underline;
  }
`;
