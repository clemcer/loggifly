import DefaultTheme from 'vitepress/theme'
import { h } from 'vue'
import './custom.css'

// export default DefaultTheme

export default {
  extends: DefaultTheme,
  Layout() {
    return h(DefaultTheme.Layout, null, {
      'sidebar-nav-after': () =>
        h('div', { style: 'padding: 16px; text-align: left;' }, [
          h(
            'a',
            {
              href: 'https://www.buymeacoffee.com/clemcer', // Ziel-Link hier einfügen
              target: '_blank',
              rel: 'noopener',
            },
            h('img', {
                src: 'https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png',
                alt: 'Logo',
                style: 'max-width: 75%; height: auto;',
            }),
        ),
        ]),
    })
  }
}