GroveScan v1.0.0
=======================

A powerful document scanning and indexing application for organizing your scanned documents with custom metadata.

INSTALLATION
------------
Run the installer as Administrator to install to Program Files.

FIRST RUN
---------
1. Start the application
2. Create or load a scanning profile
3. Connect your scanner device (or use mock scanner for testing)
4. Scan your documents
5. Assign pages with index values
6. Export organized documents

FEATURES
--------
- Dynamic indexing with custom field structures
- Support for folder hierarchy and filename generation
- Batch document scanning with page assignment
- Multiple export formats (PDF, TIFF, PNG, JPEG)
- Advanced PDF generation with ReportLab
- Profile-based workflows for different document types
- Performance optimization for large document batches
- Comprehensive help system and tooltips

SCANNER SUPPORT
---------------
- Real scanner support via PyInsane2 (Windows Image Acquisition)
- Mock scanner for testing and development
- Auto-detection of connected devices
- Configurable resolution, color modes, and formats

SYSTEM REQUIREMENTS
-------------------
- Windows 10 version 1809 (build 17763) or later
- Scanner device with Windows drivers (optional - mock mode available)
- Administrative privileges for installation
- Minimum 4GB RAM (8GB recommended for large batches)
- 1GB free disk space

PROFILES AND DATA
-----------------
User data is stored in:
- Profiles: %USERPROFILE%\Documents\GroveScan\Profiles
- Settings: %APPDATA%\GroveScan\settings.json
- Logs: %LOCALAPPDATA%\GroveScan\Logs
- Temp files: System temp directory (auto-cleaned)

PROFILE TEMPLATES
-----------------
The application includes quick-start templates for:
- Legal Documents (Client/Case/Document structure)
- Medical Records (Department/Year/Patient organization)
- Invoice Processing (Vendor/Year/Month filing)
- Archive Documents (Category/Year/Description)
- Custom profiles for any workflow

EXPORT TEMPLATES
----------------
Pre-configured export templates:
- High Quality PDF (ReportLab engine, professional output)
- Fast PDF (PIL engine, quick processing)
- Archive TIFF (multi-page, lossless compression)
- Web Images (PNG format for online use)
- Letter/A4 PDF (standard page sizes with margins)
- Email Friendly (compressed, timestamp-enabled)

TROUBLESHOOTING
---------------
Scanner Issues:
- Ensure scanner drivers are installed
- Check Windows Image Acquisition service is running
- Try refreshing device list
- Use mock scanner mode for testing without hardware

Performance:
- Reduce memory limit in Advanced settings for low-RAM systems
- Process smaller batches if experiencing memory issues
- Clear thumbnail cache if storage space is low
- Enable parallel export for faster processing

Export Problems:
- Check output directory permissions
- Ensure sufficient disk space
- Verify all pages are assigned before export
- Try different export templates

KEYBOARD SHORTCUTS
------------------
- Ctrl+N: New Profile
- Ctrl+O: Load Profile
- Ctrl+S: Save Profile
- Ctrl+E: Export Documents
- Ctrl+Shift+S: Start Scanning
- F1: Help (context-sensitive)

SUPPORT
-------
For support, feature requests, or bug reports, please contact Scanner Solutions.

Copyright (C) 2024 GroveScan Solutions