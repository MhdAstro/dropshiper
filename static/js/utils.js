// Persian number to words conversion
function numberToFarsiWords(input) {
    if (!input) return '';
    
    const num = typeof input === 'string' ? parseFloat(input) : input;
    if (isNaN(num) || num < 0) return '';
    
    if (num === 0) return 'صفر';
    
    const ones = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه'];
    const tens = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود'];
    const hundreds = ['', 'یکصد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد'];
    const teens = ['ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده'];
    
    function convertGroup(n) {
        if (n === 0) return '';
        
        let result = '';
        const h = Math.floor(n / 100);
        const remainder = n % 100;
        const t = Math.floor(remainder / 10);
        const o = remainder % 10;
        
        if (h > 0) result += hundreds[h];
        
        if (remainder >= 10 && remainder <= 19) {
            if (result) result += ' و ';
            result += teens[remainder - 10];
        } else {
            if (t >= 2) {
                if (result) result += ' و ';
                result += tens[t];
            }
            if (o > 0) {
                if (result) result += ' و ';
                result += ones[o];
            }
        }
        
        return result;
    }
    
    const integerPart = Math.floor(num);
    if (integerPart === 0) return 'صفر';
    
    let result = '';
    
    if (integerPart >= 1000000) {
        const millions = Math.floor(integerPart / 1000000);
        result += convertGroup(millions) + ' میلیون';
        const remainder = integerPart % 1000000;
        if (remainder > 0) result += ' و ';
    }
    
    const remainingAfterMillions = integerPart % 1000000;
    if (remainingAfterMillions >= 1000) {
        const thousands = Math.floor(remainingAfterMillions / 1000);
        const thousandWords = convertGroup(thousands);
        if (thousandWords) {
            if (result) result += ' ';
            result += thousandWords + ' هزار';
        }
        const remainder = remainingAfterMillions % 1000;
        if (remainder > 0) result += ' و ';
    }
    
    const finalRemainder = integerPart % 1000;
    if (finalRemainder > 0) {
        const finalWords = convertGroup(finalRemainder);
        if (result) result += ' ';
        result += finalWords;
    }
    
    return result.trim() + ' تومان';
}

// Format price with Persian digits and commas
function formatTomanPrice(price) {
    if (isNaN(price) || price === null || price === undefined) {
        return formatPersianNumber(0) + ' تومان';
    }
    
    const numberWithCommas = Math.floor(price).toLocaleString('en-US');
    const persianNumber = numberWithCommas.replace(/[0-9]/g, (digit) => {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return persianDigits[parseInt(digit)];
    });
    
    return persianNumber + ' تومان';
}

// Convert numbers to Persian digits
function formatPersianNumber(num) {
    const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    return num.toString().replace(/[0-9]/g, (digit) => persianDigits[parseInt(digit)]);
}

// Show toast notification
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

// Show loading spinner
function showLoading() {
    document.getElementById('loading-spinner').classList.remove('hidden');
}

// Hide loading spinner
function hideLoading() {
    document.getElementById('loading-spinner').classList.add('hidden');
}

// Format Persian date (simple version)
function formatPersianDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fa-IR');
}

// Get partner type in Persian
function getPartnerTypePersian(type) {
    const types = {
        'supplier': 'تامین‌کننده',
        'distributor': 'توزیع‌کننده',
        'retailer': 'خرده‌فروش',
        'manufacturer': 'تولیدکننده',
        'wholesaler': 'عمده‌فروش'
    };
    return types[type] || type;
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Generate automatic SKU code
function generateSKUCode(productName, index) {
    const timestamp = Date.now().toString().slice(-6);
    const productCode = productName ? productName.slice(0, 3).toUpperCase() : 'SKU';
    return `${productCode}-${index + 1}-${timestamp}`;
}

// Create SKU HTML
function createSKUHTML(sku, index, productName = '') {
    const autoSKUCode = sku.sku_code || generateSKUCode(productName, index);
    
    return `
        <div class="sku-item" data-index="${index}">
            <div class="sku-header">
                <h5>SKU ${index + 1}</h5>
                <button type="button" class="sku-remove" onclick="removeSKU(${index})">&times;</button>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>نام SKU *</label>
                    <input type="text" class="input-field sku-name" value="${sku.name || ''}" required>
                </div>
                <div class="form-group">
                    <label>کد SKU (خودکار)</label>
                    <input type="text" class="input-field sku-code" value="${autoSKUCode}" readonly style="background: #f8f9fa; color: #64748b;">
                    <div class="price-text" style="color: #64748b;">کد SKU به صورت خودکار تولید می‌شود</div>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>قیمت پایه (تومان) *</label>
                    <input type="number" class="input-field sku-base-price" value="${sku.base_price || ''}" min="0" required>
                    <div class="price-text sku-base-text"></div>
                </div>
                <div class="form-group">
                    <label>قیمت نهایی (تومان)</label>
                    <input type="number" class="input-field sku-final-price" value="${sku.final_price || ''}" readonly>
                    <div class="price-text sku-final-text"></div>
                </div>
            </div>
            <div class="form-group">
                <label>توضیحات</label>
                <textarea class="input-field sku-description" rows="2">${sku.description || ''}</textarea>
            </div>
        </div>
    `;
}