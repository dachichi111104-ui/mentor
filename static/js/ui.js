/**
 * Antigravity UI Helper: Modal, Toast, Drawer APIs
 */
window.modal = {
    confirm: function(options) {
        const title = options.title || 'Xác nhận thao tác';
        const message = options.message || 'Bạn có chắc chắn muốn thực hiện thao tác này?';
        const requireText = options.requireText || null;
        const onConfirm = options.onConfirm || options.callback || function() {};
        
        if (requireText) {
            const input = prompt(`${message}\n\nVui lòng gõ "${requireText}" để xác nhận:`);
            if (input === requireText) {
                onConfirm(true);
            } else {
                alert('Mã xác nhận không chính xác. Thao tác đã bị hủy.');
                onConfirm(false);
            }
        } else {
            if (window.confirm(message)) {
                onConfirm(true);
            } else {
                onConfirm(false);
            }
        }
    },
    prompt: function(options) {
        const message = options.message || 'Nhập thông tin:';
        const defaultValue = options.defaultValue || '';
        const callback = options.callback || function() {};
        const val = prompt(message, defaultValue);
        callback(val);
    }
};

window.toast = {
    show: function(msg, type = 'info') {
        console.log(`[Toast ${type}]`, msg);
    },
    success: function(msg) { this.show(msg, 'success'); },
    error: function(msg) { this.show(msg, 'error'); }
};

window.drawer = {
    open: function(id) {
        const el = document.getElementById(id);
        if (el) el.classList.remove('hidden');
    },
    close: function(id) {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    }
};
