/**
 * NZ Vintage Radio Parts Editor
 * Consolidated JavaScript for part management
 */

document.addEventListener('DOMContentLoaded', () => {
    // ======================
    // TAG MANAGEMENT SYSTEM
    // ======================
    const tagInput = document.getElementById('tag-input');
    const selectedTags = document.getElementById('selected-tags');
    let tags = [];
  
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
    if (typeof Dropzone === 'undefined') {
        console.error('Dropzone not loaded! Check script order');
        showAlert('Image upload functionality not available', 'error');
    } else {
        // Disable auto discover to prevent Dropzone from auto-initializing
        Dropzone.autoDiscover = false;
        
        // Initialize Dropzone with improved configuration
        const dropzone = new Dropzone("#dropzone", {
            url: "/upload_images",
            paramName: "files",
            maxFiles: 8,
            maxFilesize: 16, // MB
            acceptedFiles: "image/*",
            addRemoveLinks: true,
            autoProcessQueue: true, // Auto-upload when files are added
            previewsContainer: "#previewContainer",
            clickable: "#dropzone, #browseBtn",
            headers: {
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
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
                this.on("addedfile", (file) => {
                    console.log("File added:", file.name);
                });
                
                this.on("success", (file, response) => {
                    if (!response?.id) {
                        console.error("Invalid image response:", response);
                        return;
                    }
                    
                    file.serverId = response.id;
                    
                    // Create hidden input for form submission
                    const hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = 'image_ids[]';
                    hiddenInput.value = response.id;
                    document.getElementById('part-form').appendChild(hiddenInput);
                    
                    console.log(`Associated image ${response.id} with part form`);
                });
                
                this.on("totaluploadprogress", (progress) => {
                    document.getElementById("upload-progress").style.width = `${progress}%`;
                });
                
                this.on("removedfile", (file) => {
                    if (!file.serverId) return;
                    
                    const inputToRemove = document.getElementById(`image-${file.serverId}`);
                    if (inputToRemove) inputToRemove.remove();
                    
                    fetch(`/delete_image/${file.serverId}`, {
                        method: 'DELETE',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
                        }
                    }).catch(err => {
                        console.error("Deletion error:", err);
                        showAlert("Failed to delete image. Please try again.", "error");
                    });
                });
                
                this.on("error", (file, message) => {
                    showAlert(message, "error");
                    this.removeFile(file);
                });
            }
        });

        // Manual file browser trigger
        document.getElementById('browseBtn').addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.hiddenFileInput.click();
        });
    }

    // ======================
    // FORM SUBMISSION
    // ======================
    document.getElementById('part-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        console.log("Form submission started");
    
        const submitBtn = e.target.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    
        try {
            // Get all image IDs from hidden inputs
            const imageIds = [...document.querySelectorAll('input[name="image_ids[]"]')]
                .map(input => input.value)
                .filter(id => id);
            console.log("Submitting with images:", imageIds);
    
            // Prepare form data
            const formData = new FormData(e.target);
            tags.forEach(tag => formData.append('tags[]', tag));
    
            // Submit to server
            const response = await fetch('/add_part', {
                method: 'POST',
                body: formData
            });
    
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const result = await response.json();
            console.log("Server response:", result);
    
            if (result.success) {
                window.location.href = `/part/${result.part_id}`;
            } else {
                throw new Error(result.error || "Part creation failed");
            }
        } catch (err) {
            console.error("Submission failed:", err);
            showAlert(`Failed to create part: ${err.message}`, "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
});

// ======================
// HELPER FUNCTIONS
// ======================

/**
 * Display user feedback messages
 * @param {string} message - The message to display
 * @param {string} type - 'success' or 'error'
 */
function showAlert(message, type = "success") {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${type}`;
    alertDiv.textContent = message;
    document.body.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 5000);
}

/**
 * Basic HTML escaping for user-generated content
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}