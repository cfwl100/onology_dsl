package com.cfwl.oql.gql;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/** Simple CLI for converting stdin GQL-like OQL to Canonical JSON OQL. */
public final class GqlLikeOqlConverterCli {
    private GqlLikeOqlConverterCli() {
    }

    public static void main(String[] args) throws IOException {
        String schemaRef = args.length > 0 ? args[0] : "default";
        String input = new String(System.in.readAllBytes(), StandardCharsets.UTF_8);
        GqlLikeOqlConverter converter = new GqlLikeOqlConverter();
        GqlLikeOqlConverter.ConverterOptions options = GqlLikeOqlConverter.ConverterOptions.defaults().withSchemaRef(schemaRef);
        System.out.println(converter.convertToJson(input, options));
    }
}
