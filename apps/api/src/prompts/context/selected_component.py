SELECTED_COMPONENT_WITH_CODE_PROMPT = """
<user_selected_component>
    <component_name>
        {name}
    </component_name>
    <file_path>
        {file_path}
    </file_path>
    <line_number>
        {line_number}
    </line_number>
    <code>
        {code}
    </code>
    <user_requested_changes>
        {change_message}
    </user_requested_changes>
</user_selected_component>
""".strip()


SELECTED_COMPONENT_PROMPT = """
<user_selected_component>
    <component_name>
        {name}
    </component_name>
    <file_path>
        {file_path}
    </file_path>
    <line_number>
        {line_number}
    </line_number>
    <user_requested_changes>
        {change_message}
    </user_requested_changes>
</user_selected_component>
""".strip()


NO_REACT_FIBER_SELECTED_COMPONENT_PROMPT = """
<user_selected_component>
    <note>
    This component does not have the debug source, so the path is unknown. However, the children, parents, and tags are still available. The html_context shows the component inside of its parents.
    </note>
    <html_tag>
    {html_tag}
    </html_tag>
    <html_class_name>
    {html_class_name}
    </html_class_name>
    <html_children>
    {html_children}
    </html_children>
    <html_context>
    {html_context}
    </html_context>
    <user_requested_changes>
    {change_message}
    </user_requested_changes>
</user_selected_component>
""".strip()
