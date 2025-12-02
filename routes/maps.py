"""Map routes"""
from flask import render_template, request, redirect, url_for, flash, current_app
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
    
    # Get all stations with positions
    stations = Station.query.filter(
        Station.x_norm.isnot(None),
        Station.y_norm.isnot(None)
    ).all()
    
    # Get all non-ignored devices with positions
    devices = Device.query.filter(
        Device.ignored == False,
        Device.last_x_norm.isnot(None),
        Device.last_y_norm.isnot(None)
    ).all()
    
    return render_template('map.html',
                         map_data=active_map,
                         stations=stations,
                         devices=devices)


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
