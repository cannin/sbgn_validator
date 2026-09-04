package org.sbgn.schematron;

import com.helger.io.resource.IReadableResource;
import com.helger.io.resource.FileSystemResource;
import com.helger.schematron.schxslt2.xslt.SchematronResourceSchXslt2;
import com.helger.io.resource.inmemory.ReadableResourceByteArray;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import javax.xml.transform.TransformerException;
import org.w3c.dom.Document;

/** Reusable SchXslt2/Saxon reference validator for one schema and phase. */
public final class ReferenceValidator {
    private static final String SCHXSLT_PHASE_PARAMETER =
            "{http://dmaus.name/ns/2023/schxslt}phase";
    private final String schemaName;
    private final String phase;
    private final SchematronResourceSchXslt2 compiledSchema;

    /** Compile an authoritative Schematron file once.
     *
     * @param schemaPath original libSBGN schema
     * @param phase Schematron phase
     */
    public ReferenceValidator(Path schemaPath, String phase) {
        this(schemaPath.getFileName().toString(),
                new FileSystemResource(schemaPath.toAbsolutePath().normalize().toFile()), phase);
    }

    static ReferenceValidator forDocument(
            Path schemaPath, String phase, NamespacePolicy policy,
            String effectiveNamespace) throws Exception {
        SchematronNamespace.PreparedSchema prepared = SchematronNamespace.prepare(
                Files.readAllBytes(schemaPath), phase, policy, effectiveNamespace);
        IReadableResource original = new FileSystemResource(
                schemaPath.toAbsolutePath().normalize().toFile());
        return fromBytes(
                schemaPath.getFileName().toString(), prepared.data(), original, prepared.phase());
    }

    private ReferenceValidator(String schemaName, IReadableResource resource, String phase) {
        this.schemaName = schemaName;
        this.phase = phase;
        this.compiledSchema = SchematronResourceSchXslt2
                .builder(resource)
                .useCache(false)
                .phase(phase)
                // ph-schematron 10.0.1 passes the legacy unqualified parameter name,
                // while SchXslt2 1.11.2 declares the namespaced parameter below.
                .parameter(SCHXSLT_PHASE_PARAMETER, phase)
                .validateSVRL(false)
                .build();
        if (!compiledSchema.isValidSchematron()) {
            throw new IllegalArgumentException("SCHEMATRON_SCHEMA_ERROR: " + schemaName);
        }
    }

    /** Compile the packaged schema selected for an SBGN language. */
    public static ReferenceValidator builtin(String language, String phase) throws Exception {
        String name = BuiltinRules.schemaName(language);
        return new ReferenceValidator(name, BuiltinRules.resource(name), phase);
    }

    static ReferenceValidator builtinForDocument(
            String language, String phase, NamespacePolicy policy,
            String effectiveNamespace) throws Exception {
        String name = BuiltinRules.schemaName(language);
        SchematronNamespace.PreparedSchema prepared = SchematronNamespace.prepare(
                BuiltinRules.data(name), phase, policy, effectiveNamespace);
        return fromBytes(name, prepared.data(), BuiltinRules.resource(name), prepared.phase());
    }

    private static ReferenceValidator fromBytes(
            String schemaName, byte[] data, IReadableResource original, String phase) {
        ReadableResourceByteArray adjusted = new ReadableResourceByteArray(
                original.getResourceID(), data) {
            @Override
            public IReadableResource getReadableCloneForPath(String path) {
                return original.getReadableCloneForPath(path);
            }

            @Override
            public String getPath() {
                return original.getPath();
            }
        };
        return new ReferenceValidator(
                schemaName, adjusted, phase);
    }

    /** Validate one XML document with the cached compiled schema.
     *
     * @param documentPath SBGN-ML document
     * @return normalized report
     * @throws Exception when XML, compilation, or evaluation fails
     */
    public CanonicalReport validate(Path documentPath) throws Exception {
        Document svrl;
        try {
            svrl = compiledSchema.applySchematronValidation(
                    new FileSystemResource(documentPath.toAbsolutePath().normalize().toFile()));
        } catch (TransformerException exception) {
            throw new IllegalStateException("XPATH_DYNAMIC_ERROR: " + documentPath, exception);
        }
        if (svrl == null) {
            throw new IllegalStateException("INTERNAL_VALIDATOR_ERROR: no SVRL document");
        }
        List<CanonicalFinding> findings = SvrlNormalizer.normalize(svrl);
        return new CanonicalReport(
                schemaName,
                phase,
                findings.isEmpty(),
                findings,
                BackendInfo.javaOracle());
    }
}
