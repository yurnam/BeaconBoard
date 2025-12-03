"""Map routes"""
from flask import render_template, request, redirect, url_for, flash, current_app, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
import os
from models import db, Map, Station, Device
from . import routes_bp


def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@routes_bp.route('/map')
def map_view():
    """Live map view"""
    # Get active map
    active_map = Map.query.filter_by(is_active=True).first()
    
    # Get all active stations (including those without positions set)
    stations = Station.query.filter_by(active=True).all()
    
    # Get all non-ignored devices with positions
    devices = Device.query.filter(
        Device.ignored == False,
        Device.last_x_norm.isnot(None),
        Device.last_y_norm.isnot(None)
    ).all()
    
    # Convert to dicts for JSON serialization
    stations_data = [s.to_dict() for s in stations]
    devices_data = [d.to_dict() for d in devices]
    
    return render_template('map.html',
                         map_data=active_map,
                         stations=stations_data,
                         devices=devices_data)


@routes_bp.route('/map/settings')
def map_settings():
    """Map settings page"""
    maps = Map.query.order_by(Map.created_at.desc()).all()
    return render_template('map_settings.html', maps=maps)


@routes_bp.route('/map/upload', methods=['POST'])
def map_upload():
    """Upload a new map"""
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('routes.map_settings'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('routes.map_settings'))
    
    if file and allowed_file(file.filename):
        # Generate secure filename
        filename = secure_filename(file.filename)
        
        # Save file
        filepath = os.path.join(current_app.config['MAPS_FOLDER'], filename)
        file.save(filepath)
        
        # Get image dimensions
        try:
            with Image.open(filepath) as img:
                width, height = img.size
        except Exception as e:
            flash(f'Error reading image: {e}', 'error')
            os.remove(filepath)
            return redirect(url_for('routes.map_settings'))
        
        # Create map record
        map_name = request.form.get('name', filename)
        
        # Deactivate other maps
        Map.query.update({Map.is_active: False})
        
        new_map = Map(
            name=map_name,
            image_filename=filename,
            width_px=width,
            height_px=height,
            is_active=True
        )
        
        db.session.add(new_map)
        db.session.commit()
        
        flash('Map uploaded successfully', 'success')
        return redirect(url_for('routes.map_view'))
    
    flash('Invalid file type', 'error')
    return redirect(url_for('routes.map_settings'))


@routes_bp.route('/map/<int:map_id>/activate', methods=['POST'])
def map_activate(map_id):
    """Activate a map"""
    # Deactivate all maps
    Map.query.update({Map.is_active: False})
    
    # Activate selected map
    map_obj = Map.query.get(map_id)
    if map_obj:
        map_obj.is_active = True
        db.session.commit()
        flash('Map activated', 'success')
    else:
        flash('Map not found', 'error')
    
    return redirect(url_for('routes.map_settings'))


@routes_bp.route('/map/<int:map_id>/delete', methods=['POST'])
def map_delete(map_id):
    """Delete a map"""
    map_obj = Map.query.get(map_id)
    if not map_obj:
        flash('Map not found', 'error')
        return redirect(url_for('routes.map_settings'))
    
    # Prevent deletion of active map
    if map_obj.is_active:
        flash('Cannot delete the active map. Please activate another map first.', 'error')
        return redirect(url_for('routes.map_settings'))
    
    # Delete the image file
    try:
        filepath = os.path.join(current_app.config['MAPS_FOLDER'], map_obj.image_filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        # Log the error but show generic message to user
        current_app.logger.error(f'Error deleting map file {map_obj.image_filename}: {e}')
        flash('Error deleting map file', 'error')
        return redirect(url_for('routes.map_settings'))
    
    # Delete the database record
    db.session.delete(map_obj)
    db.session.commit()
    
    flash('Map deleted successfully', 'success')
    return redirect(url_for('routes.map_settings'))


@routes_bp.route('/uploads/maps/<filename>')
def serve_map(filename):
    """Serve uploaded map images"""
    # Validate filename to prevent directory traversal
    safe_filename = secure_filename(filename)
    if safe_filename != filename:
        # Filename contains unsafe characters
        return "Invalid filename", 400
    
    return send_from_directory(current_app.config['MAPS_FOLDER'], safe_filename)
