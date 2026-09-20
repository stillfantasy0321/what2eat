import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.setOptions({ gfm: true, breaks: true })

const ISSUE_FOOTER = /^\s*如果您遵循本指南的制作流程而发现有问题或可以改进的流程，请提出 Issue 或 Pull request\s*。?\s*$/gm

export function cleanRecipeMarkdown(source: string): string {
  return source
    .replace(ISSUE_FOOTER, '')
    .replace(/\n{3,}/g, '\n\n')
    .trimEnd()
}

export function renderMarkdown(source: string): string {
  return DOMPurify.sanitize(marked.parse(source) as string)
}