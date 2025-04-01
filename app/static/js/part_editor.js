/**
 * NZ Vintage Radio Parts Editor
 * Consolidated JavaScript for part management (Add/Edit)
 */

document.addEventListener('DOMContentLoaded', () => {
    // ======================
    // TAG MANAGEMENT SYSTEM
    // ======================
    const tagInput = document.getElementById('tag-input');
    const selectedTags = document.getElementById('selected-tags');
    let tags = [];

    // Initialize with existing tags if in edit mode
    if (window.partEditMode && window.existingTags) {
        tags = [...window.existingTags];
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
            <span class="tag-pill">
                ${escapeHtml(tag)} <button type="button" onclick="removeTag('${escapeHtml(tag).replace("'", "\\'")}')">✕</button>
            </span>
        `).join('');
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
    window.removeTag = (tag) => {
        tags = tags.filter(t => t !== tag);
        renderTags();
    };

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
                    'X-CSRF-Token': document.querySelector('input[name="csrf_token"]')?.value || ''
                },
                previewTemplate: `
                    <div class="dz-preview dz-file-preview">
                        <div class="dz-image">
                            <img data-dz-thumbnail />
                        </div>
                        <div class="dz-progress"><span class="dz-upload" data-dz-uploadprogress></span></div>
                        <a class="dz-remove" href="javascript:undefined;" data-dz-remove>×</a>
                    </div>
                `,
                init: function() {
                    // Add existing images in edit mode
                    if (window.partEditMode && window.existingImages) {
                        window.existingImages.forEach(image => {
                            const mockFile = {
                                name: image.filename,
                                size: image.size,
                                accepted: true,
                                url: image.url,
                                serverId: image.id,
                                existing: true
                            };
                            
                            this.emit("addedfile", mockFile);
                            this.emit("thumbnail", mockFile, mockFile.url);
                            mockFile.previewElement.classList.add("dz-complete", "dz-success");
                            
                            // Add hidden input for existing images
                            const hiddenInput = document.createElement('input');
                            hiddenInput.type = 'hidden';
                            hiddenInput.name = 'image_ids[]';
                            hiddenInput.value = image.id;
                            document.getElementById('part-form').appendChild(hiddenInput);
                        });
                    }

                    this.on("addedfile", (file) => {
                        console.log("File added:", file.name);
                    });
                    
                    this.on("success", (file, response) => {
                        if (!response?.id) {
                            console.error("Invalid image response:", response);
                            return;
                        }
                        
                        file.serverId = response.id;
                        
                        const hiddenInput = document.createElement('input');
                        hiddenInput.type = 'hidden';
                        hiddenInput.name = 'image_ids[]';
                        hiddenInput.value = response.id;
                        document.getElementById('part-form').appendChild(hiddenInput);
                    });
                    
                    this.on("totaluploadprogress", (progress) => {
                        const progressBar = document.getElementById("upload-progress");
                        if (progressBar) {
                            progressBar.style.width = `${progress}%`;
                        }
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
                        
                        // Only call delete endpoint for newly uploaded files
                        if (!file.existing) {
                            fetch(`/delete_image/${file.serverId}`, {
                                method: 'DELETE',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRF-Token': document.querySelector('input[name="csrf_token"]')?.value || ''
                                }
                            }).catch(err => {
                                console.error("Deletion error:", err);
                                showAlert("Failed to delete image. Please try again.", "error");
                            });
                        }
                    });
                    
                    this.on("error", (file, message) => {
                        showAlert(message, "error");
                        this.removeFile(file);
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
    } else {
        console.error('Dropzone not loaded! Check script order');
        showAlert('Image upload functionality not available', 'error');
    }

    // ======================
    // FORM SUBMISSION
    // ======================
    const form = document.getElementById('part-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = form.querySelector('button[type="submit"]');
            if (!submitBtn) {
                console.error("Submit button not found");
                return;
            }
            
            submitBtn.disabled = true;
            const buttonText = submitBtn.querySelector('.button-text') || submitBtn;
            const originalText = buttonText.textContent;
            buttonText.textContent = 'Saving...';
            
            try {
                const formData = new FormData(form);
                tags.forEach(tag => formData.append('tags[]', tag));
                
                if (window.partEditMode) {
                    const deletedInputs = document.querySelectorAll('input[name="deleted_images"]');
                    if (deletedInputs.length > 0) {
                        formData.append('deleted_images', deletedInputs[0].value);
                    }
                }
                
                const endpoint = window.partEditMode 
                    ? `/parts/update/${window.partId}`
                    : '/parts/add';
                
                const response = await fetch(endpoint, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRF-Token': document.querySelector('input[name="csrf_token"]')?.value || ''
                    }
                });
            
                if (!response.ok) {
                    const error = await response.json().catch(() => ({}));
                    throw new Error(error.message || `HTTP ${response.status}`);
                }
                
                const result = await response.json();
                if (result.success) {
                    window.location.href = result.redirect || `/part/${result.part_id}`;
                } else {
                    throw new Error(result.error || "Operation failed");
                }
            } catch (err) {
                console.error("Submission failed:", err);
                showAlert(`Failed to save part: ${err.message}`, "error");
            } finally {
                submitBtn.disabled = false;
                const buttonText = submitBtn.querySelector('.button-text') || submitBtn;
                buttonText.textContent = originalText;
            }
        });
    }
});

// Helper functions remain the same
function showAlert(message, type = "success") {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${type}`;
    alertDiv.textContent = message;
    document.body.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 5000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}