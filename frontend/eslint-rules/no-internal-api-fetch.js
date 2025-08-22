module.exports = {
  meta: {
    type: 'problem',
    docs: { description: 'Disallow fetch(/api/..) internal hops in server code unless whitelisted' },
    schema: []
  },
  create(context) {
    function isServerFile(filename) {
      return /app[\\/ ]api[\\/]/.test(filename) || /lib[\\/]/.test(filename);
    }
    return {
      CallExpression(node) {
        if (!node.callee) return;
        const filename = context.getFilename();
        const isFetch = node.callee.name === 'fetch';
        const isAxios = node.callee.type === 'MemberExpression' && node.callee.object.name === 'axios';
        if (!isFetch && !isAxios) return;
        if (!node.arguments.length) return;
        const arg0 = node.arguments[0];
        if (arg0.type === 'Literal' && typeof arg0.value === 'string' && arg0.value.startsWith('/api/')) {
          // Allow NextAuth and INTERNAL_PROXY_OK marked files
            if (/\/api\/auth\//.test(arg0.value)) return;
            const sourceCode = context.getSourceCode().getText();
            if (/INTERNAL_PROXY_OK/.test(sourceCode)) return;
            // For client components ("use client"), allow
            if (/^"use client";?/.test(sourceCode) || /^'use client';?/.test(sourceCode)) return;
            if (isServerFile(filename)) {
              context.report({ node: arg0, message: 'Avoid fetch("/api/*") in server code; call backend directly or mark INTERNAL_PROXY_OK.' });
            }
        }
      }
    }
  }
};
