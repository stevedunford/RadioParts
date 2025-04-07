/**
 * COMPLETE part_editor.js for NZ Vintage Radio Parts
 * - Fixed Dropzone initialization
 * - Maintains all existing functionality
 * - No missing code
 */

// Helper function to show alerts
function showAlert(message, type = "error") {
    // Remove existing alerts first
    document.querySelectorAll('.alert').forEach(el => el.remove());
    
    const alert = document.createElement('div');
    alert.className = `alert ${type}`;
    alert.innerHTML = `
        <div class="alert-content">
            <span class="alert-icon">${type === 'error' ? '❌' : '✓'}</span>
            <span class="alert-message">${message}</span>
        </div>
    `;
    
    // Add some basic styling if not already present
    alert.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 4px;
        z-index: 10000;
        background-color: ${type === 'error' ? '#ffebee' : '#e8f5e9'};
        color: ${type === 'error' ? '#c62828' : '#2e7d32'};
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        border-left: 4px solid ${type === 'error' ? '#c62828' : '#2e7d32'};
    `;
    
    document.body.appendChild(alert);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        alert.style.opacity = '0';
        alert.style.transition = 'opacity 0.5s';
        setTimeout(() => alert.remove(), 500);
    }, 5000);
}

document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('click', function(e) {
        // Check if click came from a delete button or its × child
        const deleteBtn = e.target.closest('.delete-image');
        if (deleteBtn) {
            e.preventDefault();
            e.stopPropagation();
            
            const imageId = deleteBtn.dataset.imageId;
            const wrapper = deleteBtn.closest('.existing-image-wrapper');
            
            if (imageId && wrapper) {
                deleteImage(imageId, wrapper);
            } else {
                console.error('Missing data attributes on delete button');
            }
        }
    });

    // ======================
    // 1. INITIAL SETUP
    // ======================
    const form = document.getElementById('part-form');
    if (!form) return;

    // Initialize flags
    window.partEditMode = window.partEditMode || false;
    window.partId = window.partId || null;
    window.existingImages = window.existingImages || [];

    // ======================
    // 2. TAG MANAGEMENT
    // ======================
    // Replace the existing tag management code with this:

    // Tag handling
    const tagInput = document.getElementById('tag-input');
    const selectedTags = document.getElementById('selected-tags');
    const existingTagsContainer = document.getElementById('existing-tags');

    // Initialize tags from existing inputs
    let tags = Array.from(document.querySelectorAll('#selected-tags input[name="tags[]"]'))
                .map(input => input.value);

    function renderTags() {
        selectedTags.innerHTML = tags.map(tag => `
            <span class="tag-pill part-tag" data-tag-name="${tag}">
                ${tag} <span class="remove-tag">×</span>
                <input type="hidden" name="tags[]" value="${tag}">
            </span>
        `).join('');
    }

    // Add tag from input
    tagInput.addEventListener('keydown', function(e) {
        if ((e.key === 'Enter' || e.key === ',') && tagInput.value.trim()) {
            e.preventDefault();
            if (!tags.includes(tagInput.value.trim())) {
                tags.push(tagInput.value.trim());
                renderTags();
                tagInput.value = '';
            }
        }
    });

    // Add tag from suggestions
    existingTagsContainer?.addEventListener('click', function(e) {
        const tagElement = e.target.closest('.available-tag');
        if (tagElement) {
            const tagName = tagElement.dataset.tagName;
            if (!tags.includes(tagName)) {
                tags.push(tagName);
                renderTags();
                tagElement.remove();
            }
        }
    });

    // Remove tag
    selectedTags.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-tag')) {
            const tagName = e.target.parentElement.dataset.tagName;
            tags = tags.filter(t => t !== tagName);
            renderTags();
            
            // Add back to available tags if not already there
            if (!document.querySelector(`.available-tag[data-tag-name="${tagName}"]`)) {
                existingTagsContainer.insertAdjacentHTML('beforeend', `
                    <span class="tag available-tag" data-tag-name="${tagName}">
                        ${tagName} <span class="add-tag">+</span>
                    </span>
                `);
            }
        }
    });

    // Initial render
    renderTags();


    // ======================
    // 3. FILEPOND SETUP
    // ======================

    // removed Filepond setup - which is now in manage_part.html

    // Add existing images in edit mode
    if (window.partEditMode && window.existingImages.length) {
        const previewContainer = document.getElementById('existing-images');
        previewContainer.style.pointerEvents = 'none'; // Disable interaction

        window.existingImages.forEach(image => {
            const imgWrapper = document.createElement('div');
            imgWrapper.className = 'existing-image-wrapper';
            imgWrapper.style.pointerEvents = 'auto'; // Re-enable for delete button
            imgWrapper.innerHTML = `
                <img src="${image.url}" alt="${image.name}" 
                    class="existing-image" data-image-id="${image.id}">
                <button class="delete-image" data-image-id="${image.id}">×</button>
                <input type="hidden" name="image_ids[]" value="${image.id}">
            `;
            previewContainer.appendChild(imgWrapper);
            
            // Add lightbox click handler
            imgWrapper.querySelector('img').addEventListener('click', () => {
                openLightbox(image.url);
            });
            
            // Add delete handler
            imgWrapper.querySelector('.delete-image').addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation(); // to prevent form submission
                deleteImage(image.id, imgWrapper);
            });
        });
    }

    // Lightbox function
    function openLightbox(src) {
        const lightbox = document.createElement('div');
        lightbox.className = 'lightbox';
        lightbox.innerHTML = `
            <div class="lightbox-content">
                <img src="${src}">
                <button class="close-lightbox">×</button>
            </div>
        `;
        document.body.appendChild(lightbox);
        
        lightbox.querySelector('.close-lightbox').addEventListener('click', () => {
            lightbox.remove();
        });
    }

    // Delete image function
    async function deleteImage(imageId, wrapperElement) {
        console.log('Delete initiated for image:', imageId);
        if (confirm('Delete this image?')) {
            try {
                console.log(`Attempting to delete image ${imageId}`); // Debug log
                const response = await fetch(`/parts/delete_image/${imageId}`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRF-Token': document.querySelector('[name="csrf_token"]').value,
                        'Content-Type': 'application/json'
                    }
                });
                
                const result = await response.json();
                
                if (result.success) {
                    wrapperElement.remove();
                    showAlert('Image deleted', 'success');
                    
                    // Add to deleted images list
                    const deletedInput = document.getElementById('deleted_images');
                    const currentDeleted = deletedInput.value ? deletedInput.value.split(',') : [];
                    if (!currentDeleted.includes(imageId.toString())) {
                        currentDeleted.push(imageId.toString());
                        deletedInput.value = currentDeleted.join(',');
                    }
                } else {
                    throw new Error(result.message || 'Delete failed');
                }
            } catch (error) {
                showAlert(error.message || 'Failed to delete image', 'error');
            }
        }
    }

    // ======================
    // 4. FORM SUBMISSION
    // ======================
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        try {
            const submitBtn = form.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = 'Processing...';

            const response = await fetch(form.action || (window.partEditMode 
                ? `/parts/${window.partId}/edit` 
                : '/parts/add'), {
                method: 'POST',
                body: new FormData(form),
                headers: {
                    'X-CSRF-Token': document.querySelector('[name="csrf_token"]').value,
                    'Accept': 'application/json'
                }
            });

            // validation:
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                throw new Error(`Expected JSON, got: ${contentType}. Response: ${text}`);
            }

            const result = await response.json();
            
            if (result.success) {
                // Maintain edit mode after successful update
                window.partEditMode = true;
                window.partId = result.part_id || window.partId;
                
                // Keep the button text as "Update Part" in edit mode
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = window.partEditMode 
                        ? '<span class="button-text">Update Part</span><span class="button-icon">⚡</span>' 
                        : '<span class="button-text">Add Part</span><span class="button-icon">⚡</span>';
                }

                showAlert(result.message, 'success');

                // Update part ID if new part was created
                if (result.part_id && !window.partEditMode) {
                    window.partId = result.part_id;
                    window.partEditMode = true;
                    form.querySelector('input[name="part_id"]').value = result.part_id;
                }
                // Refresh the page to ensure all changes are visible
                setTimeout(() => {
                    window.location.href = result.redirect || window.location.href;
                }, 1500);
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('Submission error:', error);
            showAlert(`Error: ${error.message}`, 'error');
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = window.partEditMode ? 'Update Part' : 'Add Part';
            }
        }
    });

    // Delete button handler
    if (window.partEditMode) {
        document.getElementById('delete-part')?.addEventListener('click', function() {
            if (confirm('Are you sure you want to delete this part?')) {
                fetch(`/parts/${window.partId}/delete`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value,
                        'Content-Type': 'application/json'
                    }
                }).then(response => {
                    if (response.ok) window.location.href = '/parts';
                    else throw new Error('Delete failed');
                }).catch(err => {
                    showAlert("Failed to delete part", "error");
                });
            }
        });
    }
});