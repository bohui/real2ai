import React, { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, X, CheckCircle, AlertCircle } from "lucide-react";

import Button from "@/components/ui/Button";
import Select from "@/components/ui/Select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { useAuthStore } from "@/store/authStore";
import { useAnalysisStore } from "@/store/analysisStore";
import { useUIStore } from "@/store/uiStore";
import { formatFileSize, australianStates, cn } from "@/utils";

const uploadSchema = z.object({
  contract_type: z.enum([
    "purchase_agreement",
    "lease_agreement",
    "off_plan",
    "auction",
  ]),
  australian_state: z.enum([
    "NSW",
    "VIC",
    "QLD",
    "SA",
    "WA",
    "TAS",
    "NT",
    "ACT",
  ]),
  user_notes: z.string().optional(),
});

type UploadFormData = z.infer<typeof uploadSchema>;

interface DocumentUploadProps {
  onUploadComplete?: (documentId: string) => void;
  onUploadError?: (error: Error) => void;
  maxFiles?: number;
  className?: string;
}

const ALLOWED_FILE_TYPES = ["pdf", "doc", "docx"];
const MAX_FILE_SIZE_MB = 10;

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadComplete,
  onUploadError,
  maxFiles = 1,
  className,
}) => {
  const { user } = useAuthStore();
  const { addNotification } = useUIStore();
  const { uploadDocument, isUploading, uploadProgress } = useAnalysisStore();

  const [selectedFiles, setSelectedFiles] = React.useState<File[]>([]);
  const [uploadedFiles, setUploadedFiles] = React.useState<
    Array<{
      file: File;
      documentId?: string;
      status: "uploading" | "completed" | "error";
      error?: string;
    }>
  >([]);
  const [uploadSuccess, setUploadSuccess] = React.useState(false);

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<UploadFormData>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      contract_type: "purchase_agreement",
      australian_state: user?.australian_state || "NSW",
      user_notes: "",
    },
  });

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      // Handle rejected files
      if (rejectedFiles.length > 0) {
        rejectedFiles.forEach(({ file, errors }) => {
          const errorMessages = errors
            .map((e: any) => {
              switch (e.code) {
                case "file-too-large":
                  return `File is too large. Maximum size is ${MAX_FILE_SIZE_MB}MB.`;
                case "file-invalid-type":
                  return `Invalid file type. Allowed types: ${ALLOWED_FILE_TYPES.join(
                    ", "
                  )}.`;
                default:
                  return e.message;
              }
            })
            .join(" ");

          addNotification({
            type: "error",
            title: "File rejected",
            message: errorMessages.includes("file-too-large")
              ? "File size too large"
              : errorMessages.includes("file-invalid-type")
              ? "File type not supported"
              : `${file.name}: ${errorMessages}`,
          });

          if (onUploadError) {
            onUploadError(new Error(errorMessages));
          }
        });
      }

      // Handle accepted files
      if (acceptedFiles.length > 0) {
        const newFiles = acceptedFiles.slice(
          0,
          maxFiles - selectedFiles.length
        );
        setSelectedFiles((prev) => [...prev, ...newFiles]);
      }
    },
    [selectedFiles, maxFiles, addNotification]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/msword": [".doc"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
    },
    maxSize: MAX_FILE_SIZE_MB * 1024 * 1024,
    multiple: maxFiles > 1,
    disabled: isUploading,
  });

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const resetUpload = () => {
    setSelectedFiles([]);
    setUploadedFiles([]);
    setUploadSuccess(false);
  };

  const onSubmit = async (data: UploadFormData) => {
    if (selectedFiles.length === 0) {
      addNotification({
        type: "warning",
        title: "No files selected",
        message: "Please select at least one file to upload.",
      });
      return;
    }

    try {
      for (const file of selectedFiles) {
        setUploadedFiles((prev) => [...prev, { file, status: "uploading" }]);

        try {
          console.log("🚀 Starting upload via store for file:", file.name);
          const documentId = await uploadDocument(
            file,
            data.contract_type,
            data.australian_state
          );
          console.log(
            "✅ Upload completed via store, document ID:",
            documentId
          );

          setUploadedFiles((prev) =>
            prev.map((item) =>
              item.file === file
                ? { ...item, documentId, status: "completed" }
                : item
            )
          );

          if (onUploadComplete) {
            console.log(
              "📞 Calling onUploadComplete with document ID:",
              documentId
            );
            onUploadComplete(documentId);
          }

          addNotification({
            type: "success",
            title: "Upload successful",
            message: `${file.name} has been uploaded and is ready for analysis.`,
          });

          setUploadSuccess(true);
        } catch (error) {
          console.error("❌ Upload failed for file:", file.name, error);
          setUploadedFiles((prev) =>
            prev.map((item) =>
              item.file === file
                ? { ...item, status: "error", error: String(error) }
                : item
            )
          );

          if (onUploadError) {
            onUploadError(error as Error);
          }
        }
      }

      // Clear selected files after upload
      setSelectedFiles([]);
    } catch (error) {
      console.error("Upload error:", error);
    }
  };

  const contractTypeOptions = [
    { value: "purchase_agreement", label: "Purchase Agreement" },
    { value: "lease_agreement", label: "Lease Agreement" },
    { value: "off_plan", label: "Off the Plan Contract" },
    { value: "auction", label: "Auction Contract" },
  ];

  return (
    <div className={cn("space-y-6", className)}>
      {/* Upload Form */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Contract Document</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Contract Type and State Selection */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Controller
                name="contract_type"
                control={control}
                render={({ field }) => (
                  <Select
                    label="Contract Type"
                    error={errors.contract_type?.message}
                    {...field}
                  >
                    {contractTypeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                )}
              />

              <Controller
                name="australian_state"
                control={control}
                render={({ field }) => (
                  <Select
                    label="Australian State"
                    error={errors.australian_state?.message}
                    {...field}
                  >
                    {australianStates.map((state) => (
                      <option key={state.value} value={state.value}>
                        {state.fullName}
                      </option>
                    ))}
                  </Select>
                )}
              />
            </div>

            {/* File Drop Zone */}
            <div
              {...getRootProps()}
              className={cn(
                "border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 cursor-pointer",
                isDragActive
                  ? "border-primary-500 bg-primary-50"
                  : "border-neutral-300 hover:border-primary-400 hover:bg-neutral-50",
                isUploading && "pointer-events-none opacity-50"
              )}
            >
              <input {...getInputProps()} />

              <div className="space-y-4">
                <div className="mx-auto w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center">
                  <Upload className="w-8 h-8 text-primary-600" />
                </div>

                <div>
                  <p className="text-lg font-medium text-neutral-900">
                    {isDragActive
                      ? "Drop your files here"
                      : "Drag & drop your contract files"}
                  </p>
                  <p className="text-sm text-neutral-500 mt-1">
                    or click to browse your computer
                  </p>
                </div>

                <div className="text-xs text-neutral-400 space-y-1">
                  <p>Supported formats: PDF, DOC, DOCX</p>
                  <p>Maximum file size: {MAX_FILE_SIZE_MB}MB</p>
                  {maxFiles > 1 && <p>Maximum {maxFiles} files</p>}
                </div>
              </div>
            </div>

            {/* Selected Files Preview */}
            <AnimatePresence>
              {selectedFiles.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-3"
                >
                  <h4 className="text-sm font-medium text-neutral-700">
                    Selected Files ({selectedFiles.length})
                  </h4>

                  {selectedFiles.map((file, index) => (
                    <motion.div
                      key={`${file.name}-${index}`}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-primary-600" />
                        <div>
                          <p className="text-sm font-medium text-neutral-900">
                            {file.name}
                          </p>
                          <p className="text-xs text-neutral-500">
                            {formatFileSize(file.size)}
                          </p>
                        </div>
                      </div>

                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(index)}
                        disabled={isUploading}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Upload Progress */}
            {isUploading && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="p-4 bg-blue-50 rounded-lg"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-primary-700">
                    Uploading...
                  </span>
                  <span className="text-sm text-primary-600">
                    {uploadProgress}%
                  </span>
                </div>
                <div className="w-full bg-primary-200 rounded-full h-2">
                  <div
                    className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </motion.div>
            )}

            {/* Notes Field */}
            <Controller
              name="user_notes"
              control={control}
              render={({ field }) => (
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Additional Notes (Optional)
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Add any specific notes about this contract..."
                    className="block w-full rounded-lg border-0 py-2.5 px-3 text-neutral-900 shadow-sm ring-1 ring-inset ring-neutral-300 placeholder:text-neutral-400 focus:ring-2 focus:ring-inset focus:ring-primary-500"
                    {...field}
                  />
                </div>
              )}
            />

            {/* Submit Button */}
            <Button
              type="submit"
              variant="primary"
              size="lg"
              fullWidth
              loading={isUploading}
              loadingText="Uploading..."
              disabled={selectedFiles.length === 0}
            >
              Upload & Continue
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Uploaded Files History */}
      {uploadedFiles.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Upload History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {uploadedFiles.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-neutral-400" />
                    <div>
                      <p className="text-sm font-medium text-neutral-900">
                        {item.file.name}
                      </p>
                      <p className="text-xs text-neutral-500">
                        {formatFileSize(item.file.size)}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {item.status === "uploading" && (
                      <div className="flex items-center gap-2 text-primary-600">
                        <div className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
                        <span className="text-xs">Uploading...</span>
                      </div>
                    )}

                    {item.status === "completed" && (
                      <div className="flex items-center gap-2 text-success-600">
                        <CheckCircle className="w-4 h-4" />
                        <span className="text-xs">Complete</span>
                      </div>
                    )}

                    {item.status === "error" && (
                      <div className="flex items-center gap-2 text-danger-600">
                        <AlertCircle className="w-4 h-4" />
                        <span className="text-xs">Error</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Upload Success State */}
      {uploadSuccess && (
        <Card>
          <CardContent className="text-center py-8">
            <CheckCircle className="w-12 h-12 text-success-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">
              Upload Successful
            </h3>
            <p className="text-neutral-600 mb-4">
              Your contract has been uploaded and is ready for analysis.
            </p>
            <Button variant="outline" onClick={resetUpload}>
              Upload Another
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export { DocumentUpload };
export default DocumentUpload;
