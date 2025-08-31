// API base URL
const API_BASE = '/api/v1';

// Generic API request function
async function apiRequest(url, options = {}) {
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };

    if (config.body && typeof config.body === 'object') {
        config.body = JSON.stringify(config.body);
    }

    try {
        const response = await fetch(API_BASE + url, config);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Products API
const productsAPI = {
    async getAll() {
        return await apiRequest('/products/');
    },

    async getById(id) {
        return await apiRequest(`/products/${id}`);
    },

    async create(productData) {
        return await apiRequest('/products/', {
            method: 'POST',
            body: productData
        });
    },

    async update(id, productData) {
        return await apiRequest(`/products/${id}`, {
            method: 'PUT',
            body: productData
        });
    },

    async delete(id) {
        return await apiRequest(`/products/${id}`, {
            method: 'DELETE'
        });
    }
};

// Partners API
const partnersAPI = {
    async getAll() {
        return await apiRequest('/partners/');
    },

    async getById(id) {
        return await apiRequest(`/partners/${id}`);
    },

    async create(partnerData) {
        return await apiRequest('/partners/', {
            method: 'POST',
            body: partnerData
        });
    },

    async update(id, partnerData) {
        return await apiRequest(`/partners/${id}`, {
            method: 'PUT',
            body: partnerData
        });
    },

    async delete(id) {
        return await apiRequest(`/partners/${id}`, {
            method: 'DELETE'
        });
    },

    async settleDebt(id, amount) {
        return await apiRequest(`/partners/${id}/settle-debt`, {
            method: 'POST',
            body: { settlement_amount: amount }
        });
    }
};

// SKUs API
const skusAPI = {
    async getAll() {
        return await apiRequest('/skus/');
    },

    async getById(id) {
        return await apiRequest(`/skus/${id}`);
    },

    async getByProductId(productId) {
        return await apiRequest(`/skus/product/${productId}`);
    },

    async create(skuData) {
        return await apiRequest('/skus/', {
            method: 'POST',
            body: skuData
        });
    },

    async update(id, skuData) {
        return await apiRequest(`/skus/${id}`, {
            method: 'PUT',
            body: skuData
        });
    },

    async delete(id) {
        return await apiRequest(`/skus/${id}`, {
            method: 'DELETE'
        });
    }
};

// Calculate final price based on partner pricing rules
async function calculateFinalPrice(basePrice, partnerId) {
    if (!basePrice || !partnerId || isNaN(basePrice) || basePrice <= 0) {
        return 0;
    }

    try {
        const partner = await partnersAPI.getById(partnerId);
        if (!partner) return basePrice;

        const profitPercentage = Number(partner.profit_percentage || 0);
        const fixedAmount = Number(partner.fixed_amount || 0);
        const priceEndingDigit = Number(partner.price_ending_digit || 0);

        // Apply pricing formula: base_price + (base_price * profit_percentage / 100) + fixed_amount
        const profitAmount = basePrice * (profitPercentage / 100);
        const calculatedPrice = basePrice + profitAmount + fixedAmount;

        // Apply price ending digit rounding if specified
        let finalPrice = calculatedPrice;
        if (priceEndingDigit > 0) {
            // Round up to the next multiple of priceEndingDigit
            const remainder = calculatedPrice % priceEndingDigit;
            if (remainder !== 0) {
                finalPrice = calculatedPrice + (priceEndingDigit - remainder);
            }
        }

        return Math.round(finalPrice);
    } catch (error) {
        console.error('Error calculating final price:', error);
        return basePrice;
    }
}

// Load dashboard stats
async function loadDashboardStats() {
    try {
        showLoading();
        
        const [products, partners] = await Promise.all([
            productsAPI.getAll(),
            partnersAPI.getAll()
        ]);

        const stats = {
            totalProducts: products.length || 0,
            totalOrders: Math.floor(Math.random() * 200) + 100, // Mock data
            totalPartners: partners.length || 0,
            totalSales: Math.floor(Math.random() * 100000) + 50000 // Mock data
        };

        // Update dashboard UI
        document.getElementById('total-products').textContent = formatPersianNumber(stats.totalProducts);
        document.getElementById('total-orders').textContent = formatPersianNumber(stats.totalOrders);
        document.getElementById('total-partners').textContent = formatPersianNumber(stats.totalPartners);
        document.getElementById('total-sales').textContent = formatTomanPrice(stats.totalSales);

        showToast('داده‌ها با موفقیت بارگیری شد', 'success');
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
        showToast('خطا در بارگیری داده‌ها', 'error');
        
        // Fallback to sample data
        document.getElementById('total-products').textContent = formatPersianNumber(25);
        document.getElementById('total-orders').textContent = formatPersianNumber(156);
        document.getElementById('total-partners').textContent = formatPersianNumber(12);
        document.getElementById('total-sales').textContent = formatTomanPrice(75000);
    } finally {
        hideLoading();
    }
}

// Load products
async function loadProducts() {
    try {
        showLoading();
        const products = await productsAPI.getAll();
        const productsGrid = document.getElementById('products-grid');
        
        if (products.length === 0) {
            productsGrid.innerHTML = '<p class="text-center text-gray-500">هیچ محصولی یافت نشد</p>';
            return;
        }

        productsGrid.innerHTML = products.map(product => `
            <div class="product-card">
                <div class="card-header">
                    <h3 class="card-title">${product.name}</h3>
                    <div class="card-actions">
                        <button class="btn-small btn-view" onclick="viewProduct('${product.id}')">مشاهده</button>
                        <button class="btn-small btn-edit" onclick="editProduct('${product.id}')">ویرایش</button>
                        <button class="btn-small btn-delete" onclick="deleteProduct('${product.id}')">حذف</button>
                    </div>
                </div>
                <div class="card-body">
                    <p><strong>دسته‌بندی:</strong> ${product.category || 'نامشخص'}</p>
                    <p><strong>برند:</strong> ${product.brand || 'نامشخص'}</p>
                    <p><strong>توضیحات:</strong> ${product.description || 'بدون توضیحات'}</p>
                    <p><strong>وضعیت:</strong> ${product.is_active ? 'فعال' : 'غیرفعال'}</p>
                </div>
            </div>
        `).join('');
        
        showToast('محصولات با موفقیت بارگیری شدند', 'success');
    } catch (error) {
        console.error('Error loading products:', error);
        showToast('خطا در بارگیری محصولات', 'error');
    } finally {
        hideLoading();
    }
}

// Load partners
async function loadPartners() {
    try {
        showLoading();
        const partners = await partnersAPI.getAll();
        const partnersGrid = document.getElementById('partners-grid');
        
        if (partners.length === 0) {
            partnersGrid.innerHTML = '<p class="text-center text-gray-500">هیچ پارتنری یافت نشد</p>';
            return;
        }

        partnersGrid.innerHTML = partners.map(partner => `
            <div class="partner-card">
                <div class="card-header">
                    <h3 class="card-title">${partner.name}</h3>
                    <div class="card-actions">
                        <button class="btn-small btn-view" onclick="viewPartnerProfile('${partner.id}')">پروفایل</button>
                        <button class="btn-small btn-edit" onclick="editPartner('${partner.id}')">ویرایش</button>
                        <button class="btn-small btn-delete" onclick="deletePartner('${partner.id}')">حذف</button>
                    </div>
                </div>
                <div class="card-body">
                    <p><strong>نوع:</strong> ${getPartnerTypePersian(partner.type)}</p>
                    <p><strong>تلفن:</strong> ${partner.contact_phone || 'نامشخص'}</p>
                    <p><strong>تعداد محصولات:</strong> ${formatPersianNumber(partner.products_count || 0)}</p>
                    <div class="debt-amount ${partner.current_debt > 0 ? '' : 'positive'}">
                        بدهی: ${formatTomanPrice(Math.abs(partner.current_debt || 0))}
                    </div>
                    ${partner.current_debt > 0 ? `
                        <button class="btn-small" style="background: rgba(220, 37, 37, 0.1); color: #DC2525; margin-top: 0.5rem;" onclick="settleDebt('${partner.id}', ${partner.current_debt})">
                            تسویه بدهی
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');
        
        showToast('پارتنرها با موفقیت بارگیری شدند', 'success');
    } catch (error) {
        console.error('Error loading partners:', error);
        showToast('خطا در بارگیری پارتنرها', 'error');
    } finally {
        hideLoading();
    }
}