package com.oac.framework.error;

public class TranslationException extends OacException {
    public TranslationException(String message) {
        super(ErrorCode.TRANSLATION_ERROR, message);
    }

    public TranslationException(String message, Throwable cause) {
        super(ErrorCode.TRANSLATION_ERROR, message, cause);
    }
}
