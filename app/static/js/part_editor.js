/**
 * NZ Vintage Radio Parts Editor
 * Consolidated JavaScript for part management (Add/Edit)
 * Fixed version with proper Dropzone integration
 */

document.addEventListener('DOMContentLoaded', () => {
    // ======================
    // TAG MANAGEMENT SYSTEM
    // ======================
    const tagInput = document.getElementById('tag-input');
    const selectedTags = document.getElementById('selected-tags');
    let tags = [];

    // Initialize with existing tags if in edit mode
    if (window.partEditMode) {
        // Get tags from hidden inputs or existing tags in the DOM
        const existingTagElements = document.querySelectorAll('#selected-tags .tag-pill');
        tags = Array.from(existingTagElements).map(el => el.textContent.trim().replace('×', ''));
        renderTags();
    }

    // Add tag on Enter or comma
    tagInput.addEventListener('keydown', (e) => {
        if ((e.key === 'Enter' || e.key === ',') && tagInput.value.trim() && tags.length < 8) {
            e.preventDefault();
            addTag(tagInput.value.trim());
        }
    });

    // Render selected tags with remove buttons
    function renderTags() {
        selectedTags.innerHTML = tags.map(tag => `
            <span class="tag-pill" data-tag-name="${escapeHtml(tag)}">
                ${escapeHtml(tag)} <span class="remove-tag">×</span>
            </span>
        `).join('');

        // Add event listeners to remove buttons
        document.querySelectorAll('.remove-tag').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tagPill = e.target.closest('.tag-pill');
                const tagName = tagPill.getAttribute('data-tag-name');
                removeTag(tagName);
            });
        });
    }

    // Add new tag
    function addTag(tag) {
        if (!tags.includes(tag) && tags.length < 8) {
            tags.push(tag);
            renderTags();
            tagInput.value = '';
        }
    }

    // Remove tag
    function removeTag(tag) {
        tags = tags.filter(t => t !== tag);
        renderTags();
    }

    // ======================
    // DROPZONE IMAGE UPLOAD
    // ======================
    if (typeof Dropzone !== 'undefined') {
        Dropzone.autoDiscover = false;
        
        // Initialize Dropzone only if the element exists
        const dropzoneElement = document.getElementById('dropzone');
        if (dropzoneElement) {
            const myDropzone = new Dropzone("#dropzone", {
                url: "/upload_images",
                paramName: "files",
                maxFiles: 8,
                maxFilesize: 16, // MB
                acceptedFiles: "image/*",
                addRemoveLinks: true,
                autoProcessQueue: true,
                previewsContainer: "#previewContainer",
                clickable: "#dropzone, #browseBtn",
                thumbnailWidth: 120,
                thumbnailHeight: 120,
                headers: {
                    'X-CSRF-Token': document.querySelector('#part-form input[name="csrf_token"]').value
                },
                previewTemplate: `
                    <div class="dz-preview dz-file-preview">
                        <div class="dz-image">
                            <img data-dz-thumbnail />
                        </div>
                        <div class="dz-details">
                            <div class="dz-filename"><span data-dz-name></span></div>
                            <div class="dz-size" data-dz-size></div>
                        </div>
                        <div class="dz-progress"><span class="dz-upload" data-dz-uploadprogress></span></div>
                        <div class="dz-error-message"><span data-dz-errormessage></span></div>
                        <a class="dz-remove" href="javascript:undefined;" data-dz-remove>×</a>
                    </div>
                `,
                init: function() {
                    // Add existing images in edit mode
                    if (window.partEditMode) {
                        const existingImages = document.querySelectorAll('.dz-preview.dz-complete');
                        existingImages.forEach(preview => {
                            const img = preview.querySelector('img');
                            const filename = preview.querySelector('.dz-filename span').textContent;
                            const removeBtn = preview.querySelector('.dz-remove');
                            const imageId = removeBtn.getAttribute('data-image-id');
                            
                            const mockFile = {
                                name: filename,
                                size: 0, // Size not available in DOM
                                accepted: true,
                                url: img.src,
                                imageId: imageId,
                                existing: true
                            };
                            
                            this.emit("addedfile", mockFile);
                            this.emit("thumbnail", mockFile, mockFile.url);
                            mockFile.previewElement.classList.add("dz-success", "dz-complete");
                            
                            // Add hidden input for existing images
                            const hiddenInput = document.createElement('input');
                            hiddenInput.type = 'hidden';
                            hiddenInput.name = 'image_ids[]';
                            hiddenInput.value = imageId;
                            document.getElementById('part-form').appendChild(hiddenInput);
                            
                            // Custom remove handler for existing images
                            removeBtn.addEventListener("click", (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                
                                if (confirm("Remove this image?")) {
                                    // Track deletion of existing image
                                    let deletedInput = document.querySelector('input[name="deleted_images"]');
                                    if (!deletedInput) {
                                        deletedInput = document.createElement('input');
                                        deletedInput.type = 'hidden';
                                        deletedInput.name = 'deleted_images';
                                        document.getElementById('part-form').appendChild(deletedInput);
                                    }
                                    deletedInput.value = deletedInput.value 
                                        ? `${deletedInput.value},${imageId}`
                                        : imageId;
                                    
                                    // Remove from Dropzone and DOM
                                    this.removeFile(mockFile);
                                    preview.remove();
                                }
                            });
                        });
                    }

                    this.on("addedfile", (file) => {
                        console.log("File added:", file.name);
                    });
                    
                    this.on("success", (file, response) => {
                        if (!response?.id) {
                            console.error("Invalid image response:", response);
                            this.removeFile(file);
                            showAlert("Image upload failed. Please try again.", "error");
                            return;
                        }
                        
                        file.serverId = response.id;
                        
                        // Add hidden input for the new image
                        const hiddenInput = document.createElement('input');
                        hiddenInput.type = 'hidden';
                        hiddenInput.name = 'image_ids[]';
                        hiddenInput.value = response.id;
                        document.getElementById('part-form').appendChild(hiddenInput);
                    });
                    
                    this.on("error", (file, message) => {
                        console.error("Upload error:", message);
                        showAlert(message, "error");
                        this.removeFile(file);
                    });
                    
                    this.on("removedfile", (file) => {
                        if (!file.serverId) return;
                        
                        // Remove associated hidden input
                        const inputs = document.querySelectorAll('input[name="image_ids[]"]');
                        inputs.forEach(input => {
                            if (input.value === file.serverId.toString()) {
                                input.remove();
                            }
                        });
                        
                        // Only call delete endpoint for newly uploaded files (not existing ones)
                        if (!file.existing) {
                            fetch(`/delete_image/${file.serverId}`, {
                                method: 'DELETE',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRF-Token': document.querySelector('input[name="csrf_token"]').value
                                }
                            }).catch(err => {
                                console.error("Deletion error:", err);
                                showAlert("Failed to delete image. Please try again.", "error");
                            });
                        }
                    });
                    
                    this.on("totaluploadprogress", (progress) => {
                        const progressBar = document.getElementById("upload-progress");
                        if (progressBar) {
                            progressBar.style.width = `${progress}%`;
                        }
                    });
                }
            });

            // Manual file browser trigger
            const browseBtn = document.getElementById('browseBtn');
            if (browseBtn) {
                browseBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    myDropzone.hiddenFileInput.click();
                });
            }
        }
    }

    // ======================
    // FORM SUBMISSION
    // ======================
    const form = document.getElementById('part-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Get CSRF token more reliably
            const csrfInput = form.querySelector('input[name="csrf_token"]');
            if (!csrfInput || !csrfInput.value) {
                showAlert("Security token missing. Please refresh the page.", "error");
                return;
            }
            const csrfToken = csrfInput.value;

            // Rest of your existing submission code...
            const endpoint = window.partEditMode 
                ? `/edit/${window.partId}`
                : '/add_part';
                
            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    body: new FormData(form), // This automatically includes the CSRF token
                    headers: {
                        // Also send as header for redundancy
                        'X-CSRF-Token': csrfToken  
                    }
                });
                // ... rest of your existing response handling ...
            } catch (err) {
                console.error("Submission failed:", err);
                showAlert(`Failed to save: ${err.message}`, "error");
            }
        });
    }
    // Delete button handler for edit mode
    if (window.partEditMode) {
        const deleteBtn = document.getElementById('delete-part');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', function() {
                if (confirm('Are you sure you want to delete this part? This cannot be undone.')) {
                    fetch(`/delete/${window.partId}`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value,
                            'Content-Type': 'application/json'
                        }
                    }).then(response => {
                        if (response.ok) {
                            window.location.href = '/gallery';
                        } else {
                            throw new Error('Delete failed');
                        }
                    }).catch(err => {
                        console.error("Delete error:", err);
                        showAlert("Failed to delete part. Please try again.", "error");
                    });
                }
            });
        }
    }
});

// Helper function to show alerts
function showAlert(message, type = "success") {
    // Remove any existing alerts first
    document.querySelectorAll('.alert').forEach(el => el.remove());
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${type}`;
    alertDiv.textContent = message;
    document.body.appendChild(alertDiv);
    
    // Position the alert (you may need to adjust this based on your layout)
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.padding = '15px 20px';
    alertDiv.style.borderRadius = '4px';
    alertDiv.style.zIndex = '10000';
    alertDiv.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    
    // Add some basic styling based on type
    if (type === "error") {
        alertDiv.style.backgroundColor = '#f44336';
        alertDiv.style.color = 'white';
    } else {
        alertDiv.style.backgroundColor = '#4CAF50';
        alertDiv.style.color = 'white';
    }
    
    setTimeout(() => {
        alertDiv.style.opacity = '0';
        alertDiv.style.transition = 'opacity 0.5s';
        setTimeout(() => alertDiv.remove(), 500);
    }, 5000);
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}