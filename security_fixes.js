// XSS 防护工具函数
function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// 内存管理 - 限制缓存大小
const MAX_CACHE_SIZE = 50000;
const MAX_MEMORY_USAGE = 0.7; // 70% 内存限制

function checkMemoryUsage() {
    if (performance.memory) {
        const usage = performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit;
        return usage < MAX_MEMORY_USAGE;
    }
    return true;
}

// 清理全局缓存
function clearGlobalCache() {
    fuzzyIndexes = {};
    s1MatchesGlobal = null;
    s2MatchesGlobal = null;
    if (window.gc) window.gc();
}

// Toast 通知替代 alert
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 6px;
        color: white;
        font-size: 14px;
        z-index: 10000;
        max-width: 400px;
        word-break: break-word;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    
    const colors = {
        info: '#3b82f6',
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444'
    };
    toast.style.background = colors[type] || colors.info;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// 操作确认对话框
function confirmAction(message) {
    return new Promise(resolve => {
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;
        
        modal.innerHTML = `
            <div style="background: var(--bg-secondary); padding: 20px; border-radius: 8px; max-width: 400px;">
                <p style="margin-bottom: 20px; color: var(--text);">${escapeHtml(message)}</p>
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button id="confirm-cancel" style="padding: 8px 16px; background: var(--bg-tertiary); border: 1px solid var(--border); color: var(--text); border-radius: 4px; cursor: pointer;">取消</button>
                    <button id="confirm-ok" style="padding: 8px 16px; background: var(--excel); border: none; color: white; border-radius: 4px; cursor: pointer;">确认</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        modal.querySelector('#confirm-cancel').onclick = () => {
            modal.remove();
            resolve(false);
        };
        modal.querySelector('#confirm-ok').onclick = () => {
            modal.remove();
            resolve(true);
        };
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.remove();
                resolve(false);
            }
        };
    });
}

// 响应式布局支持
function initResponsiveLayout() {
    const sidebar = document.querySelector('.sidebar-left');
    const toggleBtn = document.createElement('button');
    toggleBtn.innerHTML = '☰';
    toggleBtn.style.cssText = `
        position: fixed;
        left: 10px;
        top: 60px;
        z-index: 1000;
        padding: 8px 12px;
        background: var(--excel);
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        display: none;
    `;
    
    document.body.appendChild(toggleBtn);
    
    function checkWidth() {
        if (window.innerWidth < 768) {
            toggleBtn.style.display = 'block';
            sidebar.style.position = 'fixed';
            sidebar.style.left = '-100%';
            sidebar.style.width = '85%';
            sidebar.style.zIndex = '999';
            sidebar.style.transition = 'left 0.3s';
        } else {
            toggleBtn.style.display = 'none';
            sidebar.style.position = '';
            sidebar.style.left = '';
            sidebar.style.width = '';
            sidebar.style.zIndex = '';
        }
    }
    
    toggleBtn.onclick = () => {
        sidebar.style.left = sidebar.style.left === '0px' ? '-100%' : '0px';
    };
    
    window.addEventListener('resize', checkWidth);
    checkWidth();
}

// 性能监控
const perfMonitor = {
    marks: new Map(),
    start(label) {
        this.marks.set(label, performance.now());
    },
    end(label) {
        const start = this.marks.get(label);
        if (start) {
            const duration = performance.now() - start;
            console.log(`[Perf] ${label}: ${duration.toFixed(2)}ms`);
            if (duration > 1000) {
                console.warn(`[Perf] ${label} 耗时过长`);
                showToast(`${label} 处理时间较长，请耐心等待`, 'warning');
            }
        }
    }
};

// 导出修复后的函数
window.securityUtils = {
    escapeHtml,
    showToast,
    confirmAction,
    checkMemoryUsage,
    clearGlobalCache
};
window.perfMonitor = perfMonitor;
