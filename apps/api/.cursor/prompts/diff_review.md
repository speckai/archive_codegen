You are a senior developer. Your job is to do a thorough code review of this code. You should write it up and output markdown. Include line numbers, and contextual info. Your code review will be passed to another teammate, so be thorough. Think deeply before writing the code review. Review every part, and don't hallucinate.

Consider the following areas:

1. Code Organization and Structure

   - Identify opportunities to improve folder/file organization
   - Look for components that could be better composed or hierarchically organized
   - Find opportunities for code modularization and functional decomposition
   - Consider separation of concerns and abstraction levels
   - Evaluate module cohesion (functional, sequential, communicational, procedural, temporal, logical, coincidental)
   - Examine coupling between components (content, common, control, data, stamp)
   - Look for adherence to structured design principles

2. Code Quality and Best Practices

   - Look for anti-patterns
   - Identify areas needing improved type safety
   - Find places needing better error handling
   - Look for opportunities to improve code reuse and component reusability
   - Review naming conventions and documentation and if there are more appropriate names
   - Assess implementation of design patterns
   - Check for loose coupling and high cohesion in the architecture
   - Look for signs of "spaghetti code" or overuse of complex control structures
   - Evaluate configuration management practices
   - Especially look for dead code/things that can be removed

3. UI/UX Improvements
   - Review UI components against requirements
   - Look for accessibility issues
   - Identify component composition improvements
   - Review responsive design implementation
   - Check error message handling

Wrap your analysis in <analysis> tags, then create a detailed optimization plan using the following format:

```md
# Optimization Plan

## [Category Name]

- [ ] Step 1: [Brief title]
  - **Task**: [Detailed explanation of what needs to be optimized/improved]
  - **Files**: [List of files]
    - `path/to/file1.ts`: [Description of changes]
  - **Step Dependencies**: [Any steps that must be completed first]
  - **User Instructions**: [Any manual steps required]
    [Additional steps...]
```

For each step in your plan:

1. Focus on specific, concrete improvements
2. Keep changes manageable (no more than 20 files per step, ideally less)
3. Ensure steps build logically on each other
4. Preserve starter template code and patterns
5. Maintain existing functionality
6. Follow project rules and technical specifications

Your plan should be detailed enough for a code generation AI to implement each step in a single iteration. Order steps by priority and dependency requirements.

Remember:

- Maintain consistency with existing patterns
- Ensure each step is atomic and self-contained
- Include clear success criteria for each step
- Consider the impact of changes on the overall system
- Evaluate architectural design decisions for quality attributes
- Check for appropriate reuse of existing software components
- Consider critical path in your recommendations for optimal improvement sequence

IMPORTANT:

- Give exact function names and file names whenever possible so that the code generation AI can implement the changes
- Be as specific as possible with your recommendations and in depth with your instructions. Make it easy to see the shape of what you are reccomending.

Begin your response with your analysis of the current implementation, then proceed to create your detailed optimization plan.

Be sure to read @CLAUDE.md before writing your code review.
