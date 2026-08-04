import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { marked } from 'marked';

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const frontendDirectory = path.resolve(scriptDirectory, '..');
const repositoryDirectory = path.resolve(frontendDirectory, '..');
// Keep generated fragments outside `/guides`; otherwise the dev/static server
// can resolve a clean Angular route such as `/guides/demo-guide` directly to
// `demo-guide.html` and bypass the application shell.
const outputDirectory = path.join(frontendDirectory, 'public', 'guide-content');
const generatedCatalogPath = path.join(
  frontendDirectory,
  'src',
  'app',
  'features',
  'guides',
  'guide-catalog.generated.ts',
);

const guides = [
  {
    slug: 'platform-user-guide',
    source: 'docs/user-guide/platform-user-guide.md',
    title: 'Aethos PS platform user guide',
    description: 'The complete operating guide for roles, Nous, Inbox, O2C, P2P, reporting, and controls.',
    category: 'Essentials',
    audience: 'All users',
    featured: true,
    status: 'Maintained',
  },
  {
    slug: 'nous-prompt-library',
    source: 'docs/copilot/prompt-library.md',
    title: 'Aethos Nous prompt library',
    description: 'Practical prompts for daily finance operations, collections, close, controls, and demos.',
    category: 'Tutorials',
    audience: 'Finance teams',
    featured: true,
    status: 'Maintained',
  },
  {
    slug: 'scenario-demo-guide-v2',
    source: 'docs/DEMO_GUIDE_v2.md',
    title: 'Scenario-based demo guide v2',
    description: 'A full enterprise walkthrough built around realistic advisory clients and finance workflows.',
    category: 'Demo guides',
    audience: 'Demo teams',
    featured: true,
    status: 'Maintained',
  },
  {
    slug: 'demo-guide',
    source: 'docs/DEMO_GUIDE.md',
    title: 'Aethos demo guide',
    description: 'The concise engagement-to-cash, procure-to-pay, reporting, and intelligence demo route.',
    category: 'Demo guides',
    audience: 'Demo teams',
    featured: false,
    status: 'Reference',
  },
];

const guideBySource = new Map(guides.map(guide => [guide.source, guide]));

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function plainText(value) {
  return value.replace(/<[^>]*>/g, '').replaceAll('&amp;', '&').trim();
}

function headingSlug(value) {
  return plainText(value)
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || 'section';
}

function sourceLink(source, href) {
  if (/^(https?:|mailto:|tel:|#)/i.test(href)) return href;

  const normalized = path.posix.normalize(path.posix.join(path.posix.dirname(source), href));
  const publishedGuide = guideBySource.get(normalized);
  if (publishedGuide) return `/guides/${publishedGuide.slug}`;

  return `https://github.com/venkateshbr/aethos-ps/blob/main/${normalized}`;
}

async function compileGuide(guide) {
  const markdown = await readFile(path.join(repositoryDirectory, guide.source), 'utf8');
  const headings = [];
  const usedSlugs = new Map();
  const renderer = new marked.Renderer();

  renderer.heading = function ({ tokens, depth }) {
    const content = this.parser.parseInline(tokens);
    const baseSlug = headingSlug(content);
    const count = usedSlugs.get(baseSlug) ?? 0;
    usedSlugs.set(baseSlug, count + 1);
    const id = count === 0 ? baseSlug : `${baseSlug}-${count + 1}`;
    if (depth <= 3) headings.push({ id, label: plainText(content), level: depth });
    return `<h${depth} id="${id}">${content}</h${depth}>\n`;
  };

  renderer.link = function ({ href, title, tokens }) {
    const content = this.parser.parseInline(tokens);
    const resolvedHref = sourceLink(guide.source, href);
    const titleAttribute = title ? ` title="${escapeHtml(title)}"` : '';
    const external = /^https?:/i.test(resolvedHref);
    const externalAttributes = external ? ' target="_blank" rel="noreferrer"' : '';
    return `<a href="${escapeHtml(resolvedHref)}"${titleAttribute}${externalAttributes}>${content}</a>`;
  };

  // Source-controlled Markdown is the only input. Raw HTML is still escaped so
  // a future documentation edit cannot introduce executable markup.
  renderer.html = ({ text }) => `<pre><code>${escapeHtml(text)}</code></pre>`;

  const html = await marked.parse(markdown, { gfm: true, renderer });
  const wordCount = markdown.trim().split(/\s+/).length;
  const catalogEntry = {
    ...guide,
    readMinutes: Math.max(1, Math.ceil(wordCount / 220)),
    headings: headings.filter(heading => heading.level === 2 || heading.level === 3),
  };

  await writeFile(path.join(outputDirectory, `${guide.slug}.html`), html, 'utf8');
  return catalogEntry;
}

await mkdir(outputDirectory, { recursive: true });
await mkdir(path.dirname(generatedCatalogPath), { recursive: true });

const catalog = [];
for (const guide of guides) catalog.push(await compileGuide(guide));

const generatedSource = `// Generated by scripts/generate-guides.mjs. Do not edit directly.\n\n`
  + `export interface GuideHeading {\n  id: string;\n  label: string;\n  level: number;\n}\n\n`
  + `export interface GuideEntry {\n`
  + `  slug: string;\n  source: string;\n  title: string;\n  description: string;\n`
  + `  category: string;\n  audience: string;\n  featured: boolean;\n  status: string;\n`
  + `  readMinutes: number;\n  headings: GuideHeading[];\n}\n\n`
  + `export const GUIDE_CATALOG: GuideEntry[] = ${JSON.stringify(catalog, null, 2)};\n`;

await writeFile(generatedCatalogPath, generatedSource, 'utf8');
console.log(`Generated ${catalog.length} guides in ${outputDirectory}`);
