$(document).ready(function () {
    console.log('Document ready');

    // Drag-and-drop functionality for the entire page
    var dragDropArea = $('#dragDropArea');

    dragDropArea.on('dragover', function (e) {
        e.preventDefault();
        dragDropArea.addClass('dragover');
    });

    dragDropArea.on('dragleave', function (e) {
        e.preventDefault();
        dragDropArea.removeClass('dragover');
    });

    dragDropArea.on('drop', function (e) {
        e.preventDefault();
        dragDropArea.removeClass('dragover');

        var files = e.originalEvent.dataTransfer.files;
        if (files.length > 0) {
            // Check if there's an empty upload field
            var emptySection = $('.upload-section').filter(function () {
                var fileInput = $(this).find('.fileInput')[0];
                return fileInput && fileInput.files.length === 0;
            }).first();

            if (emptySection.length > 0) {
                // Use the empty section
                var fileInput = emptySection.find('.fileInput')[0];
                var dataTransfer = new DataTransfer();
                dataTransfer.items.add(files[0]);
                fileInput.files = dataTransfer.files;

                // Trigger change event to show the thumbnail
                $(fileInput).trigger('change');
            } else {
                // Create a new file input section for the dropped file
                var newSection = `
                    <div class="upload-section">
                        <div class="mb-3">
                            <input type="file" class="form-control fileInput" name="file" accept=".jpg, .jpeg, .png, .gif" required>
                            <small class="form-text text-muted">Allowed file types: JPG, JPEG, PNG, GIF</small>
                        </div>
                        <button type="button" class="btn btn-secondary btn-sm remove-btn">Remove</button>
                        <div class="progress mt-3" style="height: 20px;">
                            <div class="progress-bar" role="progressbar" style="width: 0%;">0%</div>
                        </div>
                        <div class="status mt-3"></div>
                        <div class="selectedThumbnail mt-3"></div>
                        <div class="uploadedThumbnail mt-3"></div>
                    </div>
                `;
                $('#uploadSections').append(newSection);

                // Simulate file selection for the new section
                var fileInput = $('#uploadSections .upload-section').last().find('.fileInput')[0];
                var dataTransfer = new DataTransfer();
                dataTransfer.items.add(files[0]);
                fileInput.files = dataTransfer.files;

                // Trigger change event to show the thumbnail
                $(fileInput).trigger('change');
            }
        }
    });

    // Add a new file input section
    $('#addFileInput').on('click', function () {
        console.log('Add Another File clicked');
        var newSection = `
            <div class="upload-section">
                <div class="mb-3">
                    <input type="file" class="form-control fileInput" name="file" accept=".jpg, .jpeg, .png, .gif" required>
                    <small class="form-text text-muted">Allowed file types: JPG, JPEG, PNG, GIF</small>
                </div>
                <button type="button" class="btn btn-secondary btn-sm remove-btn">Remove</button>
                <div class="progress mt-3" style="height: 20px;">
                    <div class="progress-bar" role="progressbar" style="width: 0%;">0%</div>
                </div>
                <div class="status mt-3"></div>
                <div class="selectedThumbnail mt-3"></div>
                <div class="uploadedThumbnail mt-3"></div>
            </div>
        `;
        $('#uploadSections').append(newSection);
    });

    // Remove a file input section
    $(document).on('click', '.remove-btn', function () {
        console.log('Remove button clicked');
        $(this).closest('.upload-section').remove();
    });

    // Show thumbnail when a file is selected
    $(document).on('change', '.fileInput', function (e) {
        console.log('File input changed');
        var file = e.target.files[0];
        var section = $(this).closest('.upload-section');
        if (file && file.type.startsWith('image/')) {
            var reader = new FileReader();
            reader.onload = function (e) {
                section.find('.selectedThumbnail').html(
                    `<img src="${e.target.result}" class="thumbnail thumbnail-small" alt="Selected Thumbnail">`
                );
            };
            reader.readAsDataURL(file);
        } else {
            section.find('.selectedThumbnail').html(''); // Clear thumbnail if file is not an image
        }
    });

    // Upload all files
    $('#uploadAll').on('click', function () {
        console.log('Upload All clicked');
        var sections = $('.upload-section');
        console.log('Number of sections:', sections.length);

        sections.each(function () {
            var section = $(this);
            var fileInput = section.find('.fileInput')[0];

            // Check if fileInput exists
            if (!fileInput) {
                console.log('No file input found in this section');
                return; // Skip this section
            }

            var file = fileInput.files[0];

            console.log('Processing section:', section);
            console.log('File:', file);

            if (!file) {
                console.log('No file selected in this section');
                section.find('.status').html('<div class="alert alert-danger">No file selected.</div>');
                return;
            }

            // Frontend validation: Check file type
            var allowedTypes = ['image/jpeg', 'image/png', 'image/gif'];
            if (!allowedTypes.includes(file.type)) {
                console.log('Invalid file type:', file.type);
                section.find('.status').html('<div class="alert alert-danger">Error: Only JPG, PNG, and GIF files are allowed.</div>');
                return;
            }

            // Frontend validation: Check file size (5MB maximum)
            var maxSize = 5 * 1024 * 1024; // 5MB
            if (file.size > maxSize) {
                console.log('File too large:', file.size);
                section.find('.status').html('<div class="alert alert-danger">Error: File size must be less than 5MB.</div>');
                return;
            }

            var formData = new FormData();
            formData.append('file', file);

            console.log('Sending AJAX request for file:', file.name);

            $.ajax({
                url: '/upload',
                type: 'POST',
                data: formData,
                processData: false, // Prevent jQuery from processing the data
                contentType: false, // Prevent jQuery from setting content type
                xhr: function () {
                    var xhr = new XMLHttpRequest();
                    xhr.upload.addEventListener('progress', function (e) {
                        if (e.lengthComputable) {
                            var percent = Math.round((e.loaded / e.total) * 100);
                            section.find('.progress-bar').css('width', percent + '%').text(percent + '%');
                        }
                    }, false);
                    return xhr;
                },
                success: function (response) {
                    console.log('Upload successful for file:', file.name);
                    // Collapse the section into a compact view
                    section.html(`
                        <div class="uploaded-file">
                            <img src="${URL.createObjectURL(file)}" class="thumbnail thumbnail-small" alt="Uploaded Thumbnail">
                            <div class="filename">${file.name}</div>
                            <button type="button" class="btn btn-danger btn-sm delete-btn" data-filename="${file.name}">Delete</button>
                        </div>
                    `);
                },
                error: function (xhr, status, error) {
                    console.log('Upload failed for file:', file.name, 'Error:', error);
                    section.find('.status').html('<div class="alert alert-danger">Error: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Upload failed') + '</div>');
                }
            });
        });
    });

    // Delete an uploaded file
    $(document).off('click', '.delete-image').on('click', '.delete-image', function(e) {
        console.log('Delete button clicked');
        e.stopPropagation(); // Prevent event bubbling
        var filename = $(this).data('filename');
        var section = $(this).closest('.upload-section');

        $.ajax({
            url: '/delete',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ filename: filename }),
            success: function (response) {
                console.log('File deleted:', filename);
                section.remove(); // Remove the section from the UI
            },
            error: function (xhr, status, error) {
                console.log('Failed to delete file:', filename, 'Error:', error);
                alert('Error: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Failed to delete file'));
            }
        });
    });

    // Delete all uploaded files
    $('#deleteAll').on('click', function () {
        console.log('Delete All clicked');
        var uploadedFiles = $('.uploaded-file');

        if (uploadedFiles.length === 0) {
            alert('No files to delete.');
            return;
        }

        if (confirm('Are you sure you want to delete all files?')) {
            uploadedFiles.each(function () {
                var section = $(this).closest('.upload-section');
                var deleteBtn = section.find('.delete-btn');
                var filename = deleteBtn.data('filename');

                // Send delete request
                $.ajax({
                    url: '/delete',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ filename: filename }),
                    success: function (response) {
                        console.log('File deleted:', filename);
                        section.remove(); // Remove the section from the UI
                    },
                    error: function (xhr, status, error) {
                        console.log('Failed to delete file:', filename, 'Error:', error);
                        alert('Error: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Failed to delete file'));
                    }
                });
            });
        }
    });
});


// Save description
$(document).on('click', '.save-description', function () {
    var imageId = $(this).data('image-id');
    var description = $(`.description-input[data-image-id="${imageId}"]`).val();

    $.ajax({
        url: `/update_description/${imageId}`,
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ description: description }),
        success: function (response) {
            alert('Description updated successfully');
        },
        error: function (xhr, status, error) {
            alert('Error: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Failed to update description'));
        }
    });
});

// Add tag
$(document).on('click', '.add-tag', function () {
    var imageId = $(this).data('image-id');
    var tag = $(`.tag-input[data-image-id="${imageId}"]`).val();

    $.ajax({
        url: `/add_tag/${imageId}`,
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ tag: tag }),
        success: function (response) {
            alert('Tag added successfully');
            location.reload(); // Refresh the page to show the new tag
        },
        error: function (xhr, status, error) {
            alert('Error: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Failed to add tag'));
        }
    });
});

// Delete image
$(document).on('click', '.delete-image', function () {
    var imageId = $(this).data('image-id');

    if (confirm('Are you sure you want to delete this image?')) {
        $.ajax({
            url: `/delete/${imageId}`,
            type: 'POST',
            success: function (response) {
                alert('Image deleted successfully');
                location.reload(); // Refresh the page to reflect the deletion
            },
            error: function (xhr, status, error) {
                alert('Error: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Failed to delete image'));
            }
        });
    }
});


$(document).ready(function () {
    // Save description
    $(document).on('click', '.save-description', function () {
        var imageId = $(this).data('image-id');
        var description = $(`.description-input[data-image-id="${imageId}"]`).val();

        $.ajax({
            url: `/update_description/${imageId}`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ description: description }),
            success: function (response) {
                alert('Description updated successfully');
            },
            error: function (xhr, status, error) {
                alert('Error: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Failed to update description'));
            }
        });
    });

    // Add tag
    $(document).on('click', '.add-tag', function () {
        var imageId = $(this).data('image-id');
        var tag = $(`.tag-input[data-image-id="${imageId}"]`).val();

        $.ajax({
            url: `/add_tag/${imageId}`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ tag: tag }),
            success: function (response) {
                alert('Tag added successfully');
                location.reload(); // Refresh the page to show the new tag
            },
            error: function (xhr, status, error) {
                alert('Error: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Failed to add tag'));
            }
        });
    });

    // Delete image
    $(document).on('click', '.delete-image', function () {
        var imageId = $(this).data('image-id');

        if (confirm('Are you sure you want to delete this image?')) {
            $.ajax({
                url: `/delete/${imageId}`,
                type: 'POST',
                success: function (response) {
                    alert('Image deleted successfully');
                    location.reload(); // Refresh the page to reflect the deletion
                },
                error: function (xhr, status, error) {
                    alert('Error: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Failed to delete image'));
                }
            });
        }
    });
});

function initGalleryModal() {
    document.addEventListener('DOMContentLoaded', function() {
        document.addEventListener('click', function(e) {
            // 1. Find the closest card
            const card = e.target.closest('.card');
            if (!card) return;
    
            // 2. Get all required elements
            const img = card.querySelector('.gallery-img');
            if (!img) return;
    
            // 3. Get tags - with multiple fallbacks
            let tagsHTML = '';
            const tagsContainer = card.querySelector('.tags');
            
            if (tagsContainer) {
                // Clone the tags container to preserve original
                const tagsClone = tagsContainer.cloneNode(true);
                
                // Process tags for modal display
                tagsClone.querySelectorAll('a').forEach(tag => {
                    tag.classList.add('modal-tag'); // Add special class
                    tag.style.pointerEvents = 'none'; // Make unclickable
                });
                
                tagsHTML = tagsClone.innerHTML;
            } else {
                tagsHTML = '<span class="text-muted">No tags</span>';
            }
    
            // 4. Update modal elements
            const modal = document.getElementById('imageModal');
            const modalImg = document.getElementById('modalImage');
            const modalTitle = document.getElementById('modalTitle');
            const modalTags = document.getElementById('modalTags');
            
            if (!modal || !modalImg || !modalTitle || !modalTags) {
                console.error("Missing modal elements!");
                return;
            }
    
            modalImg.src = img.src;
            modalTitle.textContent = img.dataset.description || "No description";
            modalTags.innerHTML = tagsHTML;
    
            // 5. Show modal
            new bootstrap.Modal(modal).show();
        });
    });
}

// Tag validation constants
const MAX_TAGS_PER_IMAGE = 8;
const MAX_TAG_LENGTH = 20;

// Validate before adding tags
function validateTag(tag) {
    return tag.length <= MAX_TAG_LENGTH;
}

// Check existing tags
function countTags(imageId) {
    return document.querySelectorAll(`[data-image-id="${imageId}"] .badge`).length;
}