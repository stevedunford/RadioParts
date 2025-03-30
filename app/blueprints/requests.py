@bp.route('/request-part', methods=['POST'])
def request_part():
    """Email librarian about a part"""
    part = Part.query.get(request.form['part_id'])
    send_email(
        to=part.location.librarian_email,
        subject=f"Part Request: {part.name}",
        body=f"Requester: {request.form['email']}\nNotes: {request.form['notes']}"
    )
    flash("Request sent! The librarian will contact you soon.")
    return redirect(url_for('parts.detail', part_id=part.id))