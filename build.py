#!/usr/bin/env python3
"""
Bitcoin Calculadora - Build System
Ensambla páginas HTML a partir de includes compartidos + contenido específico de cada página.

Uso:
  python3 build.py              # Build completo
  python3 build.py --watch      # Watch mode (requiere watchdog, opcional)

Estructura:
  src/_includes/    → Componentes compartidos (header, nav, footer, etc.)
  src/_pages/       → Páginas con frontmatter YAML + contenido HTML
  src/css/          → Estilos (se copian tal cual)
  src/js/           → JavaScript (se copia tal cual)
  docs/             → Output final (GitHub Pages sirve desde aquí o desde root)
"""

import os
import re
import shutil
import sys
import json
from pathlib import Path

# Rutas
SRC_DIR = Path(__file__).parent / 'src'
INCLUDES_DIR = SRC_DIR / '_includes'
PAGES_DIR = SRC_DIR / '_pages'
OUTPUT_DIR = Path(__file__).parent / 'docs'

# ─────────────────────────────────────────────
# Frontmatter parser (YAML-like, sin dependencias)
# ─────────────────────────────────────────────

def parse_frontmatter(content):
    """
    Extrae frontmatter delimitado por --- al inicio del archivo.
    Soporta valores simples key: value y bloques multilínea con key: |
    El cierre --- debe estar solo en su propia línea (no dentro de comentarios).
    """
    if not content.startswith('---'):
        return {}, content
    
    # Find closing --- that is on its own line
    lines = content.split('\n')
    end_line = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_line = i
            break
    
    if end_line == -1:
        return {}, content
    
    frontmatter_str = '\n'.join(lines[1:end_line])
    body = '\n'.join(lines[end_line + 1:]).strip()
    
    meta = {}
    current_key = None
    current_value_lines = []
    
    for line in frontmatter_str.split('\n'):
        # Check if this is a new key
        if re.match(r'^[a-z_]+:', line) and not line.strip().startswith('#'):
            # Save previous key if exists
            if current_key:
                meta[current_key] = '\n'.join(current_value_lines).strip()
            
            key, _, value = line.partition(':')
            current_key = key.strip()
            value = value.strip()
            
            if value == '|':
                # Multiline value
                current_value_lines = []
            else:
                current_value_lines = [value]
        elif current_key:
            current_value_lines.append(line)
    
    # Save last key
    if current_key:
        meta[current_key] = '\n'.join(current_value_lines).strip()
    
    return meta, body


# ─────────────────────────────────────────────
# Template engine (mustache-like, minimal)
# ─────────────────────────────────────────────

def render_template(template, context):
    """
    Motor de plantillas mínimo:
    - {{variable}}           → Reemplaza por valor
    - {{var|default}}        → Valor o default
    - {{#section}}...{{/section}}  → Muestra bloque si variable es truthy
    - {{>include_name}}      → Incluye archivo de _includes/
    """
    
    # 1. Resolver includes {{>name}}
    def resolve_include(match):
        include_name = match.group(1).strip()
        include_path = INCLUDES_DIR / f'{include_name}.html'
        if include_path.exists():
            include_content = include_path.read_text(encoding='utf-8')
            # Recursively render the include with same context
            return render_template(include_content, context)
        else:
            print(f'  ⚠️  Include not found: {include_name}')
            return f'<!-- include {include_name} not found -->'
    
    template = re.sub(r'\{\{>\s*(.+?)\s*\}\}', resolve_include, template)
    
    # 2. Conditional sections {{#key}}...{{/key}}
    def resolve_section(match):
        key = match.group(1)
        content = match.group(2)
        value = context.get(key, '')
        if value and value not in ('false', '0', ''):
            return content
        return ''
    
    template = re.sub(r'\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}', resolve_section, template, flags=re.DOTALL)
    
    # 3. Variables with defaults {{var|default}}
    def resolve_var_default(match):
        key = match.group(1).strip()
        default = match.group(2).strip()
        value = context.get(key, '')
        if value:
            return value
        # Default might contain other variables
        return render_template(default, context) if '{{' in default else default
    
    template = re.sub(r'\{\{(\w+)\|(.+?)\}\}', resolve_var_default, template)
    
    # 4. Simple variables {{var}}
    def resolve_var(match):
        key = match.group(1).strip()
        return str(context.get(key, ''))
    
    template = re.sub(r'\{\{(\w+)\}\}', resolve_var, template)
    
    return template


# ─────────────────────────────────────────────
# Layout wrapper
# ─────────────────────────────────────────────

TOOL_LAYOUT = """<!DOCTYPE html>
<html lang="es">
<head>
{{>head}}
{{#extra_styles}}
  <style>
{{extra_styles}}
  </style>
{{/extra_styles}}
</head>
<body>

  <div class="site-nav">
    <div class="nav-inner">
      <div class="nav-top">
        <a href="/" class="nav-brand">
          <svg class="btc-logo" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="50" fill="#f7931a"/><path d="M67.8 44.3c1-6.6-4-10.2-10.9-12.5l2.2-8.9-5.4-1.3-2.2 8.7c-1.4-.4-2.9-.7-4.3-1l2.2-8.7-5.4-1.3-2.2 8.9c-1.2-.3-2.3-.5-3.4-.8l-7.5-1.9-1.4 5.8s4 .9 3.9 1c2.2.5 2.6 2 2.5 3.1l-2.5 10.2c.2 0 .3.1.5.1l-.5-.1-3.6 14.3c-.3.7-.9 1.7-2.5 1.3.1.1-3.9-1-3.9-1L22 66l7 1.7c1.3.3 2.6.7 3.9 1l-2.3 9 5.4 1.3 2.2-8.9c1.5.4 2.9.8 4.3 1.1l-2.2 8.8 5.4 1.3 2.3-9c9.3 1.8 16.3.7 19.3-7.4 2.4-6.5-.1-10.3-4.8-12.7 3.4-.8 6-3.1 6.7-7.9zM58 55c-1.7 6.8-13.2 3.1-16.9 2.2l3-12.1c3.7.9 15.7 2.8 13.9 9.9zm1.7-17.5c-1.6 6.2-11.1 3-14.2 2.3l2.7-11c3.1.8 13.2 2.2 11.5 8.7z" fill="#fff"/></svg>
          <span>Bitcoin Calculadora</span>
          <span class="nav-subtitle">{{subtitle}}</span>
        </a>
        <button class="nav-hamburger" onclick="document.querySelector('.nav-calculadoras').classList.toggle('open');this.textContent=this.textContent==='☰'?'✕':'☰'" aria-label="Menú">☰</button>
      </div>
{{>nav}}
    </div>
  </div>

  <main class="container">

{{content}}

  </main>

  <script src="/js/main.js"></script>
{{#extra_scripts}}
{{extra_scripts}}
{{/extra_scripts}}
</body>
</html>"""

BLOG_LAYOUT = """<!DOCTYPE html>
<html lang="es">
<head>
{{>head}}
</head>
<body>

  <div class="site-nav">
    <div class="nav-inner">
      <div class="nav-top">
        <a href="/" class="nav-brand">
          <svg class="btc-logo" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="50" fill="#f7931a"/><path d="M67.8 44.3c1-6.6-4-10.2-10.9-12.5l2.2-8.9-5.4-1.3-2.2 8.7c-1.4-.4-2.9-.7-4.3-1l2.2-8.7-5.4-1.3-2.2 8.9c-1.2-.3-2.3-.5-3.4-.8l-7.5-1.9-1.4 5.8s4 .9 3.9 1c2.2.5 2.6 2 2.5 3.1l-2.5 10.2c.2 0 .3.1.5.1l-.5-.1-3.6 14.3c-.3.7-.9 1.7-2.5 1.3.1.1-3.9-1-3.9-1L22 66l7 1.7c1.3.3 2.6.7 3.9 1l-2.3 9 5.4 1.3 2.2-8.9c1.5.4 2.9.8 4.3 1.1l-2.2 8.8 5.4 1.3 2.3-9c9.3 1.8 16.3.7 19.3-7.4 2.4-6.5-.1-10.3-4.8-12.7 3.4-.8 6-3.1 6.7-7.9zM58 55c-1.7 6.8-13.2 3.1-16.9 2.2l3-12.1c3.7.9 15.7 2.8 13.9 9.9zm1.7-17.5c-1.6 6.2-11.1 3-14.2 2.3l2.7-11c3.1.8 13.2 2.2 11.5 8.7z" fill="#fff"/></svg>
          <span>Bitcoin Calculadora</span>
        </a>
        <button class="nav-hamburger" onclick="document.querySelector('.nav-calculadoras').classList.toggle('open');this.textContent=this.textContent==='☰'?'✕':'☰'" aria-label="Menú">☰</button>
      </div>
{{>nav}}
    </div>
  </div>

  <main class="container">

{{content}}

{{>footer-blog}}
  </main>
</body>
</html>"""

BLOG_ARTICLE_LAYOUT = """<!DOCTYPE html>
<html lang="es">
<head>
{{>head}}
</head>
<body>

  <div class="site-nav">
    <div class="nav-inner">
      <div class="nav-top">
        <a href="/" class="nav-brand">
          <svg class="btc-logo" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="50" fill="#f7931a"/><path d="M67.8 44.3c1-6.6-4-10.2-10.9-12.5l2.2-8.9-5.4-1.3-2.2 8.7c-1.4-.4-2.9-.7-4.3-1l2.2-8.7-5.4-1.3-2.2 8.9c-1.2-.3-2.3-.5-3.4-.8l-7.5-1.9-1.4 5.8s4 .9 3.9 1c2.2.5 2.6 2 2.5 3.1l-2.5 10.2c.2 0 .3.1.5.1l-.5-.1-3.6 14.3c-.3.7-.9 1.7-2.5 1.3.1.1-3.9-1-3.9-1L22 66l7 1.7c1.3.3 2.6.7 3.9 1l-2.3 9 5.4 1.3 2.2-8.9c1.5.4 2.9.8 4.3 1.1l-2.2 8.8 5.4 1.3 2.3-9c9.3 1.8 16.3.7 19.3-7.4 2.4-6.5-.1-10.3-4.8-12.7 3.4-.8 6-3.1 6.7-7.9zM58 55c-1.7 6.8-13.2 3.1-16.9 2.2l3-12.1c3.7.9 15.7 2.8 13.9 9.9zm1.7-17.5c-1.6 6.2-11.1 3-14.2 2.3l2.7-11c3.1.8 13.2 2.2 11.5 8.7z" fill="#fff"/></svg>
          <span>Bitcoin Calculadora</span>
        </a>
        <button class="nav-hamburger" onclick="document.querySelector('.nav-calculadoras').classList.toggle('open');this.textContent=this.textContent==='☰'?'✕':'☰'" aria-label="Menú">☰</button>
      </div>
{{>nav}}
    </div>
  </div>

  <main class="container">

{{content}}

{{>affiliates}}

{{>footer-blog}}
  </main>
</body>
</html>"""


def get_layout(layout_name):
    layouts = {
        'tool': TOOL_LAYOUT,
        'blog': BLOG_LAYOUT,
        'blog-article': BLOG_ARTICLE_LAYOUT,
    }
    return layouts.get(layout_name, TOOL_LAYOUT)


# ─────────────────────────────────────────────
# Build process
# ─────────────────────────────────────────────

def build_page(page_path, relative_path):
    """Build a single page from source."""
    content = page_path.read_text(encoding='utf-8')
    meta, body = parse_frontmatter(content)
    
    if not meta:
        # No frontmatter = raw file, copy as-is
        return content
    
    # Set up context with all meta
    context = dict(meta)
    
    # Pre-render the body content (resolve includes like {{>affiliates}} in content)
    rendered_body = render_template(body, context)
    context['content'] = rendered_body
    
    # Get layout
    layout_name = meta.get('layout', 'tool')
    layout = get_layout(layout_name)
    
    # Render the full page
    rendered = render_template(layout, context)
    
    return rendered


def build():
    """Full build: process all pages, copy static assets."""
    print('🔨 Building Bitcoin Calculadora...\n')
    
    # Clean output
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    
    # Copy static assets
    for static_dir in ['css', 'js']:
        src_static = SRC_DIR / static_dir
        if src_static.exists():
            dst_static = OUTPUT_DIR / static_dir
            shutil.copytree(src_static, dst_static)
            print(f'  📁 Copied {static_dir}/')
    
    # Copy CNAME if exists
    cname = SRC_DIR / 'CNAME'
    if cname.exists():
        shutil.copy2(cname, OUTPUT_DIR / 'CNAME')
        print('  📄 Copied CNAME')
    
    # Copy robots.txt and sitemap.xml if they exist
    for extra_file in ['robots.txt', 'sitemap.xml']:
        src_file = SRC_DIR / extra_file
        if src_file.exists():
            shutil.copy2(src_file, OUTPUT_DIR / extra_file)
            print(f'  📄 Copied {extra_file}')
    
    # Build pages
    page_count = 0
    for page_path in PAGES_DIR.rglob('*.html'):
        relative = page_path.relative_to(PAGES_DIR)
        
        # Determine output path
        # _pages/index.html → docs/index.html
        # _pages/conversor.html → docs/conversor/index.html
        # _pages/blog/index.html → docs/blog/index.html
        # _pages/blog/que-es-dca.html → docs/blog/que-es-dca/index.html
        
        if relative.name == 'index.html':
            out_path = OUTPUT_DIR / relative
        elif relative.parent == Path('.'):
            # Top-level page like conversor.html → conversor/index.html
            out_path = OUTPUT_DIR / relative.stem / 'index.html'
        else:
            # Nested page like blog/que-es-dca.html → blog/que-es-dca/index.html
            out_path = OUTPUT_DIR / relative.parent / relative.stem / 'index.html'
        
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        rendered = build_page(page_path, relative)
        out_path.write_text(rendered, encoding='utf-8')
        
        page_count += 1
        print(f'  ✅ {relative} → {out_path.relative_to(OUTPUT_DIR)}')
    
    print(f'\n🎉 Build complete! {page_count} pages generated in docs/')


if __name__ == '__main__':
    build()
