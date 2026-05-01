/**
 * Utility to format Multer file objects for the database.
 * Maps the original name and the unique disk name.
 */
export const formatFile = (file) =>
  file
    ? {
        fileName: file.originalname,
        fileChangedName: file.filename,
        filePath: `/uploads/${file.filename}`,
      }
    : null;

/**
 * Handles the logic of updating a file. 
 * If a new file is uploaded, it formats it; 
 * otherwise, it returns the existing file record.
 */
export const handleFileUpdate = (existingFile, newFileArray) => {
  if (newFileArray && newFileArray.length > 0) {
    return formatFile(newFileArray[0]);
  }
  return existingFile; // Keep the old record if no new file is provided
};