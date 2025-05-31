// Confirm before deleting
document.addEventListener('DOMContentLoaded', function() {
    const deleteButtons = document.querySelectorAll('.button.danger');

    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this product?')) {
                e.preventDefault();
            }
        });
    });
});