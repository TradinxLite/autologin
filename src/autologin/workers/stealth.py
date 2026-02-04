
"""
Stealth scripts for Playwright to evade bot detection.
"""

def get_stealth_scripts() -> list[str]:
    """
    Returns a list of JavaScript scripts to be injected into the browser context
    to mask automation indicators.
    """
    scripts = []

    # 1. Remove navigator.webdriver property
    scripts.append("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    # 2. Mock window.chrome
    scripts.append("""
        window.chrome = {
            runtime: {},
            app: {
                InstallState: {
                    DISABLED: 'disabled',
                    INSTALLED: 'installed',
                    NOT_INSTALLED: 'not_installed'
                },
                RunningState: {
                    CANNOT_RUN: 'cannot_run',
                    READY_TO_RUN: 'ready_to_run',
                    RUNNING: 'running'
                },
                getDetails: function() {},
                getIsInstalled: function() {},
                installState: function() {},
                isInstalled: false,
                runningState: function() {}
            },
            csi: function() {},
            loadTimes: function() {}
        };
    """)

    # 3. Mock Permissions API
    scripts.append("""
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    """)

    # 4. Mock Plugins and MimeTypes
    # This provides a basic set of plugins to look more realistic
    scripts.append("""
        (function() {
            function mockPluginsAndMimeTypes() {
                const makePluginArray = (plugins) => {
                    const pluginArray = plugins.map(p => p);
                    pluginArray.refresh = () => {};
                    pluginArray.namedItem = (name) => pluginArray.find(p => p.name === name);
                    pluginArray.item = (index) => pluginArray[index];
                    return pluginArray;
                }

                const pluginData = [
                    {
                        name: 'PDF Viewer',
                        filename: 'internal-pdf-viewer',
                        description: 'Portable Document Format',
                        mimeTypes: [{ type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }]
                    },
                    {
                        name: 'Chrome PDF Viewer',
                        filename: 'internal-pdf-viewer',
                        description: 'Portable Document Format',
                        mimeTypes: [{ type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format' }]
                    },
                    {
                        name: 'Chromium PDF Viewer',
                        filename: 'internal-pdf-viewer',
                        description: 'Portable Document Format',
                        mimeTypes: [{ type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format' }]
                    },
                    {
                        name: 'Microsoft Edge PDF Viewer',
                        filename: 'internal-pdf-viewer',
                        description: 'Portable Document Format',
                        mimeTypes: [{ type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }]
                    },
                    {
                        name: 'WebKit built-in PDF',
                        filename: 'internal-pdf-viewer',
                        description: 'Portable Document Format',
                        mimeTypes: [{ type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }]
                    }
                ];

                const plugins = [];
                const mimeTypes = [];

                pluginData.forEach(data => {
                    const mtypes = data.mimeTypes.map(mt => {
                        const mimeType = {
                            type: mt.type,
                            suffixes: mt.suffixes,
                            description: mt.description,
                            __pluginName: data.name
                        };
                        mimeTypes.push(mimeType);
                        return mimeType;
                    });

                    const plugin = {
                        name: data.name,
                        filename: data.filename,
                        description: data.description,
                        length: mtypes.length,
                        item: (index) => mtypes[index],
                        namedItem: (name) => mtypes.find(mt => mt.type === name),
                        0: mtypes[0] 
                    };
                    
                    plugins.push(plugin);
                });
                
                // Link MimeTypes to Plugins
                mimeTypes.forEach(mt => {
                    mt.enabledPlugin = plugins.find(p => p.name === mt.__pluginName);
                    delete mt.__pluginName; // cleanup
                });

                const pluginArray = makePluginArray(plugins);
                const mimeTypeArray = makePluginArray(mimeTypes);

                Object.defineProperty(navigator, 'plugins', {
                    get: () => pluginArray
                });

                Object.defineProperty(navigator, 'mimeTypes', {
                    get: () => mimeTypeArray
                });
            }
            
            mockPluginsAndMimeTypes();
        })();
    """)
    
    # 5. Mask WebGL Vendor/Renderer
    scripts.append("""
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // UNMASKED_VENDOR_WEBGL
            if (parameter === 37445) {
                return 'Google Inc. (Google)';
            }
            // UNMASKED_RENDERER_WEBGL
            if (parameter === 37446) {
                return 'ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)';
            }
            return getParameter(parameter);
        };
    """)
    
    # 6. Randomize User Agent Platform if needed (Optional, usually handled by BrowserContext options)
    # But we can override platform property
    scripts.append("""
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32'
        });
    """)

    return scripts
