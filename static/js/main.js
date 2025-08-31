// Global variables
let currentProduct = null;
let currentPartner = null;
let skuCounter = 0;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
});

function initializeApp() {
    // Load initial data
    loadDashboardStats();
    loadProducts();
    loadPartners();
    
    // Load partners for product form
    loadPartnersForSelect();
    
    // Hide loading spinner after initial load
    setTimeout(hideLoading, 1000);
}

function setupEventListeners() {
    // Navigation tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            const tabName = e.target.dataset.tab;
            switchTab(tabName);
        });
    });

    // Modal close buttons
    document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
        btn.addEventListener('click', closeModals);
    });

    // Modal overlays (click outside to close)
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                closeModals();
            }
        });
    });

    // Add buttons
    document.getElementById('add-product-btn').addEventListener('click', () => openProductModal());
    document.getElementById('add-partner-btn').addEventListener('click', () => openPartnerModal());
    document.getElementById('add-sku-btn').addEventListener('click', addSKU);

    // Form submissions
    document.getElementById('product-form').addEventListener('submit', saveProduct);
    document.getElementById('partner-form').addEventListener('submit', savePartner);

    // Partner pricing fields with real-time conversion
    setupPartnerPricingListeners();
}

function switchTab(tabName) {
    // Update nav tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Load data if needed
    if (tabName === 'products') {
        loadProducts();
    } else if (tabName === 'partners') {
        loadPartners();
    } else if (tabName === 'dashboard') {
        loadDashboardStats();
    }
}

function closeModals() {
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.classList.remove('show');
    });
    currentProduct = null;
    currentPartner = null;
}

// Product Modal Functions
function openProductModal(productId = null) {
    const modal = document.getElementById('product-modal');
    const title = document.getElementById('product-modal-title');
    const form = document.getElementById('product-form');
    
    if (productId) {
        title.textContent = 'ویرایش محصول';
        loadProductData(productId);
    } else {
        title.textContent = 'افزودن محصول جدید';
        form.reset();
        document.getElementById('skus-container').innerHTML = '';
        skuCounter = 0;
        currentProduct = null;
    }
    
    modal.classList.add('show');
}

async function loadProductData(productId) {
    try {
        showLoading();
        currentProduct = await productsAPI.getById(productId);
        
        // Fill form fields
        document.getElementById('product-name').value = currentProduct.name || '';
        document.getElementById('product-description').value = currentProduct.description || '';
        document.getElementById('product-category').value = currentProduct.category || '';
        document.getElementById('product-brand').value = currentProduct.brand || '';
        document.getElementById('product-partner').value = currentProduct.partner_id || '';
        
        // Load SKUs
        const skus = await skusAPI.getByProductId(productId);
        const container = document.getElementById('skus-container');
        container.innerHTML = '';
        skuCounter = 0;
        
        skus.forEach((sku, index) => {
            container.innerHTML += createSKUHTML(sku, index, currentProduct.name);
            skuCounter++;
        });
        
        // Setup SKU event listeners
        setupSKUListeners();
        
    } catch (error) {
        console.error('Error loading product data:', error);
        showToast('خطا در بارگیری اطلاعات محصول', 'error');
    } finally {
        hideLoading();
    }
}

async function saveProduct(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const productData = {
        name: document.getElementById('product-name').value.trim(),
        description: document.getElementById('product-description').value.trim() || null,
        category: document.getElementById('product-category').value.trim() || null,
        brand: document.getElementById('product-brand').value.trim() || null,
        partner_id: document.getElementById('product-partner').value || null,
        is_active: true
    };

    // Collect SKUs data
    const skus = [];
    document.querySelectorAll('.sku-item').forEach((skuItem, index) => {
        const name = skuItem.querySelector('.sku-name').value.trim();
        const skuCode = skuItem.querySelector('.sku-code').value.trim();
        const basePrice = parseFloat(skuItem.querySelector('.sku-base-price').value) || 0;
        const finalPrice = parseFloat(skuItem.querySelector('.sku-final-price').value) || 0;
        const description = skuItem.querySelector('.sku-description').value.trim();
        
        if (name && basePrice > 0) {
            skus.push({
                name,
                sku_code: skuCode || generateSKUCode(productData.name, index),
                base_price: basePrice,
                final_price: finalPrice,
                description: description || null,
                is_active: true
            });
        }
    });

    try {
        showLoading();
        
        let savedProduct;
        if (currentProduct && currentProduct.id) {
            savedProduct = await productsAPI.update(currentProduct.id, productData);
            showToast('محصول با موفقیت به‌روزرسانی شد', 'success');
        } else {
            savedProduct = await productsAPI.create(productData);
            showToast('محصول با موفقیت ایجاد شد', 'success');
        }

        // Save SKUs
        for (const skuData of skus) {
            skuData.product_id = savedProduct.id;
            await skusAPI.create(skuData);
        }

        closeModals();
        loadProducts();
        
    } catch (error) {
        console.error('Error saving product:', error);
        showToast('خطا در ذخیره محصول', 'error');
    } finally {
        hideLoading();
    }
}

// Partner Modal Functions
function openPartnerModal(partnerId = null) {
    const modal = document.getElementById('partner-modal');
    const title = document.getElementById('partner-modal-title');
    const form = document.getElementById('partner-form');
    
    if (partnerId) {
        title.textContent = 'ویرایش پارتنر';
        loadPartnerData(partnerId);
    } else {
        title.textContent = 'افزودن پارتنر جدید';
        form.reset();
        currentPartner = null;
        clearPricingTexts();
    }
    
    modal.classList.add('show');
}

async function loadPartnerData(partnerId) {
    try {
        showLoading();
        currentPartner = await partnersAPI.getById(partnerId);
        
        // Fill form fields
        document.getElementById('partner-name').value = currentPartner.name || '';
        document.getElementById('partner-type').value = currentPartner.type || 'supplier';
        document.getElementById('partner-phone').value = currentPartner.contact_phone || '';
        document.getElementById('partner-address').value = currentPartner.address || '';
        document.getElementById('partner-description').value = currentPartner.description || '';
        document.getElementById('partner-profit').value = currentPartner.profit_percentage || '';
        document.getElementById('partner-fixed').value = currentPartner.fixed_amount || '';
        document.getElementById('partner-ending').value = currentPartner.price_ending_digit || '';
        
        // Update pricing texts
        updatePricingTexts();
        
    } catch (error) {
        console.error('Error loading partner data:', error);
        showToast('خطا در بارگیری اطلاعات پارتنر', 'error');
    } finally {
        hideLoading();
    }
}

async function savePartner(e) {
    e.preventDefault();
    
    const partnerData = {
        name: document.getElementById('partner-name').value.trim(),
        type: document.getElementById('partner-type').value,
        contact_phone: document.getElementById('partner-phone').value.trim(),
        address: document.getElementById('partner-address').value.trim() || null,
        description: document.getElementById('partner-description').value.trim() || null,
        profit_percentage: parseFloat(document.getElementById('partner-profit').value) || 0,
        fixed_amount: parseFloat(document.getElementById('partner-fixed').value) || 0,
        price_ending_digit: parseInt(document.getElementById('partner-ending').value) || 0,
        is_active: true
    };

    try {
        showLoading();
        
        if (currentPartner && currentPartner.id) {
            await partnersAPI.update(currentPartner.id, partnerData);
            showToast('پارتنر با موفقیت به‌روزرسانی شد', 'success');
        } else {
            await partnersAPI.create(partnerData);
            showToast('پارتنر با موفقیت ایجاد شد', 'success');
        }

        closeModals();
        loadPartners();
        loadPartnersForSelect();
        
    } catch (error) {
        console.error('Error saving partner:', error);
        showToast('خطا در ذخیره پارتنر', 'error');
    } finally {
        hideLoading();
    }
}

// SKU Functions
function addSKU() {
    const container = document.getElementById('skus-container');
    const productName = document.getElementById('product-name').value || 'محصول';
    const newSKU = { name: '', sku_code: '', base_price: '', final_price: '', description: '' };
    container.innerHTML += createSKUHTML(newSKU, skuCounter, productName);
    skuCounter++;
    setupSKUListeners();
}

function removeSKU(index) {
    const skuItem = document.querySelector(`[data-index="${index}"]`);
    if (skuItem) {
        skuItem.remove();
    }
}

function setupSKUListeners() {
    document.querySelectorAll('.sku-base-price').forEach(input => {
        input.addEventListener('input', debounce(async (e) => {
            const skuItem = e.target.closest('.sku-item');
            const basePrice = parseFloat(e.target.value);
            const partnerId = document.getElementById('product-partner').value;
            
            if (basePrice > 0 && partnerId) {
                const finalPrice = await calculateFinalPrice(basePrice, partnerId);
                const finalPriceInput = skuItem.querySelector('.sku-final-price');
                const basePriceText = skuItem.querySelector('.sku-base-text');
                const finalPriceText = skuItem.querySelector('.sku-final-text');
                
                finalPriceInput.value = finalPrice;
                basePriceText.textContent = numberToFarsiWords(basePrice);
                finalPriceText.textContent = numberToFarsiWords(finalPrice);
            }
        }, 500));
    });
}

// Partner pricing event listeners
function setupPartnerPricingListeners() {
    const profitInput = document.getElementById('partner-profit');
    const fixedInput = document.getElementById('partner-fixed');
    const endingInput = document.getElementById('partner-ending');
    
    if (profitInput) {
        profitInput.addEventListener('input', updatePricingTexts);
    }
    if (fixedInput) {
        fixedInput.addEventListener('input', updatePricingTexts);
    }
    if (endingInput) {
        endingInput.addEventListener('input', updatePricingTexts);
    }
}

function updatePricingTexts() {
    const profitValue = parseFloat(document.getElementById('partner-profit').value) || 0;
    const fixedValue = parseFloat(document.getElementById('partner-fixed').value) || 0;
    const endingValue = parseFloat(document.getElementById('partner-ending').value) || 0;
    
    document.getElementById('profit-text').textContent = profitValue > 0 ? `${profitValue}% سود` : '';
    document.getElementById('fixed-text').textContent = fixedValue > 0 ? numberToFarsiWords(fixedValue) : '';
    document.getElementById('ending-text').textContent = endingValue > 0 ? numberToFarsiWords(endingValue) : '';
}

function clearPricingTexts() {
    document.getElementById('profit-text').textContent = '';
    document.getElementById('fixed-text').textContent = '';
    document.getElementById('ending-text').textContent = '';
}

// Action Functions
async function viewProduct(productId) {
    try {
        showLoading();
        const product = await productsAPI.getById(productId);
        const skus = await skusAPI.getByProductId(productId);
        
        // Create product view modal content
        const modal = document.getElementById('partner-profile-modal');
        const content = document.getElementById('partner-profile-content');
        
        content.innerHTML = `
            <div class="product-view">
                <h4>${product.name}</h4>
                <div class="profile-info">
                    <p><strong>توضیحات:</strong> ${product.description || 'بدون توضیحات'}</p>
                    <p><strong>دسته‌بندی:</strong> ${product.category || 'نامشخص'}</p>
                    <p><strong>برند:</strong> ${product.brand || 'نامشخص'}</p>
                    <p><strong>وضعیت:</strong> ${product.is_active ? 'فعال' : 'غیرفعال'}</p>
                    <p><strong>تاریخ ایجاد:</strong> ${formatPersianDate(product.created_at)}</p>
                </div>
                
                ${skus.length > 0 ? `
                    <div class="skus-section" style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid #e2e8f0;">
                        <h5 style="margin-bottom: 1rem;">SKU های محصول:</h5>
                        ${skus.map(sku => `
                            <div class="sku-info" style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                                <p><strong>نام:</strong> ${sku.name}</p>
                                <p><strong>کد SKU:</strong> ${sku.sku_code || 'خودکار'}</p>
                                <p><strong>قیمت پایه:</strong> ${formatTomanPrice(sku.base_price || 0)}</p>
                                <p><strong>قیمت نهایی:</strong> ${formatTomanPrice(sku.final_price || 0)}</p>
                                ${sku.description ? `<p><strong>توضیحات:</strong> ${sku.description}</p>` : ''}
                            </div>
                        `).join('')}
                    </div>
                ` : '<p style="margin-top: 1rem; color: #64748b;">هیچ SKU برای این محصول تعریف نشده</p>'}
            </div>
        `;
        
        modal.classList.add('show');
    } catch (error) {
        console.error('Error loading product view:', error);
        showToast('خطا در بارگیری اطلاعات محصول', 'error');
    } finally {
        hideLoading();
    }
}

async function editProduct(productId) {
    openProductModal(productId);
}

async function deleteProduct(productId) {
    if (!confirm('آیا مطمئن هستید که می‌خواهید این محصول را حذف کنید؟')) {
        return;
    }
    
    try {
        showLoading();
        await productsAPI.delete(productId);
        showToast('محصول با موفقیت حذف شد', 'success');
        loadProducts();
    } catch (error) {
        console.error('Error deleting product:', error);
        showToast('خطا در حذف محصول', 'error');
    } finally {
        hideLoading();
    }
}

async function editPartner(partnerId) {
    openPartnerModal(partnerId);
}

async function deletePartner(partnerId) {
    if (!confirm('آیا مطمئن هستید که می‌خواهید این پارتنر را حذف کنید؟')) {
        return;
    }
    
    try {
        showLoading();
        await partnersAPI.delete(partnerId);
        showToast('پارتنر با موفقیت حذف شد', 'success');
        loadPartners();
        loadPartnersForSelect();
    } catch (error) {
        console.error('Error deleting partner:', error);
        showToast('خطا در حذف پارتنر', 'error');
    } finally {
        hideLoading();
    }
}

async function viewPartnerProfile(partnerId) {
    try {
        showLoading();
        const partner = await partnersAPI.getById(partnerId);
        const modal = document.getElementById('partner-profile-modal');
        const content = document.getElementById('partner-profile-content');
        
        content.innerHTML = `
            <div class="partner-profile">
                <h4>${partner.name}</h4>
                <div class="profile-info">
                    <p><strong>نوع:</strong> ${getPartnerTypePersian(partner.type)}</p>
                    <p><strong>تلفن:</strong> ${partner.contact_phone || 'نامشخص'}</p>
                    <p><strong>آدرس:</strong> ${partner.address || 'نامشخص'}</p>
                    <p><strong>توضیحات:</strong> ${partner.description || 'بدون توضیحات'}</p>
                    <p><strong>درصد سود:</strong> ${partner.profit_percentage || 0}%</p>
                    <p><strong>مبلغ ثابت:</strong> ${formatTomanPrice(partner.fixed_amount || 0)}</p>
                    <p><strong>رقم آخر قیمت:</strong> ${formatTomanPrice(partner.price_ending_digit || 0)}</p>
                    <p><strong>بدهی فعلی:</strong> ${formatTomanPrice(partner.current_debt || 0)}</p>
                    <p><strong>تعداد محصولات:</strong> ${formatPersianNumber(partner.products_count || 0)}</p>
                </div>
            </div>
        `;
        
        modal.classList.add('show');
    } catch (error) {
        console.error('Error loading partner profile:', error);
        showToast('خطا در بارگیری پروفایل پارتنر', 'error');
    } finally {
        hideLoading();
    }
}

async function settleDebt(partnerId, debtAmount) {
    if (!confirm(`آیا مطمئن هستید که می‌خواهید بدهی ${formatTomanPrice(debtAmount)} را تسویه کنید؟`)) {
        return;
    }
    
    try {
        showLoading();
        await partnersAPI.settleDebt(partnerId, debtAmount);
        showToast('بدهی با موفقیت تسویه شد', 'success');
        loadPartners();
    } catch (error) {
        console.error('Error settling debt:', error);
        showToast('خطا در تسویه بدهی', 'error');
    } finally {
        hideLoading();
    }
}

// Load partners for select dropdown
async function loadPartnersForSelect() {
    try {
        const partners = await partnersAPI.getAll();
        const select = document.getElementById('product-partner');
        
        // Clear existing options except the first one
        const firstOption = select.querySelector('option[value=""]');
        select.innerHTML = '';
        if (firstOption) {
            select.appendChild(firstOption);
        }
        
        partners.forEach(partner => {
            const option = document.createElement('option');
            option.value = partner.id;
            option.textContent = partner.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading partners for select:', error);
    }
}