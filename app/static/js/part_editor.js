/**
 * Part Editor - Universal form handler for adding and editing parts
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get form and initialize variables
    const form = document.getElementById('part-form');
    if (!form) return;
    
    // Detect if we're in edit mode
    const isEditMode = window.partEditMode || false;
    const partId = window.partId || null;
    const uploadedImages = [];
    let deletedImages = window.deletedImages || [];

    // Initialize Dropzone for file uploads
    const myDropzone = new Dropzone("#dropzone", {
        url: "/parts/upload_images",
        paramName: "files",
        maxFilesize: 16, // MB
        acceptedFiles: "image/jpeg,image/png,image/gif",
        addRemoveLinks: true,
        maxFiles: 8,
        uploadMultiple: false,
        autoProcessQueue: true,
        createImageThumbnails: true,
        dictDefaultMessage: "Drop files here to upload",
        previewsContainer: "#previewContainer",
        clickable: "#browseBtn",
        init: function() {
            // Add existing images in edit mode
            if (isEditMode && window.existingImages) {
                window.existingImages.forEach(file => {
                    // Create mock file for existing images
                    const mockFile = {
                        name: file.name,
                        size: file.size,
                        accepted: true,
                        dataURL: file.url,
                        status: "success",
                        imageId: file.id
                    };
                    
                    // Add to dropzone with custom image ID
                    myDropzone.emit("addedfile", mockFile);
                    myDropzone.emit("thumbnail", mockFile, file.url);
                    myDropzone.emit("complete", mockFile);
                    myDropzone.files.push(mockFile);
                });
            }
        }
    });

    // Update progress bar during upload
    myDropzone.on("totaluploadprogress", function(progress) {
        document.getElementById("upload-progress").style.width = progress + "%";
    });

    // Handle successful uploads - store image ID for form submission
    myDropzone.on("success", function(file, response) {
        if (response && response.id) {
            file.imageId = response.id;
            uploadedImages.push(response.id);
        }
    });

    // Handle removed files
    myDropzone.on("removedfile", function(file) {
        // If file has an imageId, it's a server-side file
        if (file.imageId) {
            // In edit mode, track deleted image IDs
            if (isEditMode) {
                deletedImages.push(file.imageId);
                const deletedImagesInput = document.getElementById('deleted_images');
                if (deletedImagesInput) {
                    deletedImagesInput.value = deletedImages.join(',');
                }
            }
            
            // Remove from uploaded images if it was just added
            const index = uploadedImages.indexOf(file.imageId);
            if (index > -1) {
                uploadedImages.splice(index, 1);
            }
        }
    });

    // Tag management
    const tagInput = document.getElementById('tag-input');
    const selectedTagsContainer = document.getElementById('selected-tags');
    
    // Add tag from input
    if (tagInput) {
        tagInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                
                let tagName = this.value.trim();
                if (tagName) {
                    addTag(tagName);
                    this.value = '';
                }
            }
        });
    }
    
    // Function to add a tag to the UI and form
    function addTag(tagName) {
        // Limit to 8 tags
        const existingTags = document.querySelectorAll('input[name="tags[]"]');
        if (existingTags.length >= 8) {
            alert('Maximum 8 tags allowed');
            return;
        }
        
        // Check if tag already exists
        for (let i = 0; i < existingTags.length; i++) {
            if (existingTags[i].value.toLowerCase() === tagName.toLowerCase()) {
                return; // Tag already exists
            }
        }
        
        // Create visual tag pill
        const tagPill = document.createElement('span');
        tagPill.className = 'tag-pill';
        tagPill.textContent = tagName + ' ×';
        tagPill.addEventListener('click', function() {
            this.parentNode.removeChild(this);
            
            // Find and remove the hidden input
            const inputs = selectedTagsContainer.querySelectorAll('input[name="tags[]"]');
            for (let i = 0; i < inputs.length; i++) {
                if (inputs[i].value === tagName) {
                    inputs[i].parentNode.removeChild(inputs[i]);
                    break;
                }
            }
        });
        
        // Create hidden input for form submission
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = 'tags[]';
        hiddenInput.value = tagName;
        
        // Add to container
        selectedTagsContainer.appendChild(tagPill);
        selectedTagsContainer.appendChild(hiddenInput);
    }
    
    // Handle existing tag pills (for edit mode)
    document.querySelectorAll('.tag-pill').forEach(pill => {
        pill.addEventListener('click', function() {
            const tagName = this.textContent.replace(' ×', '');
            
            // Remove the pill
            this.parentNode.removeChild(this);
            
            // Find and remove the hidden input
            const inputs = selectedTagsContainer.querySelectorAll('input[name="tags[]"]');
            for (let i = 0; i < inputs.length; i++) {
                if (inputs[i].value === tagName) {
                    inputs[i].parentNode.removeChild(inputs[i]);
                    break;
                }
            }
        });
    });

    // Form submission handler - common for add/edit
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate form (basic validation)
        const name = document.getElementById('name').value;
        const brandId = form.querySelector('select[name="brand_id"]').value;
        const typeId = form.querySelector('select[name="part_type_id"]').value;
        
        if (!name || !brandId || !typeId) {
            alert('Please fill in all required fields');
            return;
        }
        
        // Create FormData object
        const formData = new FormData(form);
        
        // Add uploaded image IDs
        uploadedImages.forEach(id => {
            formData.append('image_ids[]', id);
        });
        
        // Determine endpoint based on mode
        const endpoint = isEditMode 
            ? `/parts/edit/${partId}`
            : '/parts/add_part';
        
        // Submit the form
        fetch(endpoint, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Handle success
            if (data.success) {
                // Redirect to new part page or stay on form with message
                if (data.redirect) {
                    window.location.href = data.redirect;
                } else if (data.part_id) {
                    window.location.href = `/parts/part/${data.part_id}`;
                } else {
                    alert('Part saved successfully!');
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error saving part: ' + error.message);
        });
    });
});