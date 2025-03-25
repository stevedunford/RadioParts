$(document).ready(function() {
    // Create new tag
    $('#createTagForm').submit(function(e) {
        e.preventDefault();
        const tagName = $('#newTagName').val().trim();
        
        if (tagName) {
            $.ajax({
                url: '/api/tags',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ name: tagName }),
                success: function() {
                    location.reload();
                },
                error: function(xhr) {
                    alert('Error: ' + (xhr.responseJSON?.error || 'Failed to create tag'));
                }
            });
        }
    });

    // Rename tag
    $('.rename-tag').click(function() {
        const tagId = $(this).data('tag-id');
        const currentName = $(this).closest('li').find('a').text().trim();
        const newName = prompt('Enter new name for tag:', currentName);
        
        if (newName && newName !== currentName) {
            $.ajax({
                url: `/api/tags/${tagId}`,
                method: 'PUT',
                contentType: 'application/json',
                data: JSON.stringify({ name: newName }),
                success: function() {
                    location.reload();
                },
                error: function(xhr) {
                    alert('Error: ' + (xhr.responseJSON?.error || 'Failed to rename tag'));
                }
            });
        }
    });

    // Delete tag
    $('.delete-tag').click(function() {
        if (confirm('Are you sure you want to delete this tag?')) {
            const tagId = $(this).data('tag-id');
            
            $.ajax({
                url: `/api/tags/${tagId}`,
                method: 'DELETE',
                success: function() {
                    location.reload();
                },
                error: function(xhr) {
                    alert('Error: ' + (xhr.responseJSON?.error || 'Failed to delete tag'));
                }
            });
        }
    });

    // Merge tags
    $('#mergeTagsForm').submit(function(e) {
        e.preventDefault();
        const tagsToMerge = $('#tagsToMerge').val();
        const mergeInto = $('#mergeInto').val();
        
        if (tagsToMerge.length < 1) {
            alert('Please select at least one tag to merge');
            return;
        }
        
        if (confirm('Merge selected tags? This cannot be undone.')) {
            $.ajax({
                url: `/api/tags/merge`,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ 
                    source_ids: tagsToMerge, 
                    target_id: mergeInto 
                }),
                success: function() {
                    location.reload();
                },
                error: function(xhr) {
                    alert('Error: ' + (xhr.responseJSON?.error || 'Failed to merge tags'));
                }
            });
        }
    });
});