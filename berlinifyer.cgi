#!/usr/bin/perl -wT
# This cgi-script translates webpages to the dialect spoken in Berlin, Germany.
#
# Copyright (C) 2002-2003 Ramiro Gómez <ramiro@rahoo.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the same terms as Perl itself.
use strict;

# If you need to specify additional paths to perl modules, do it here, e.g.:
# use lib qw(/home/pub/lib/perl5/site_perl/5.6.1);
use URI; # for absolutizing urls
use CGI qw(-no_xhtml); # output HTML
use Carp;

# Security measures
$CGI::POST_MAX=1024*100;  # max 100 KBytes posts
$CGI::DISABLE_UPLOADS = 1;  # no uploads

# Globals
my $berlinified = undef; # String, where CGI-output is saved
my $outfile = undef;
my $q = new CGI; # cgi object
my $new_query = $q->script_name() . '?url='; # prepend to links to berlinify the whole www

# locale settings for \w matching ü,ö,ä
use locale;
use POSIX 'locale_h';
setlocale(LC_CTYPE, 'de_DE') or croak "Invalid locale";

if ($q->param()) {
    my $url = $q->param('url');
    unless ( ($url =~ m|^((?:[^:/?#]+:)?(?://[^/?#]*)?[^?#]*(?:\?[^#]*)?(?:#.*)?)| )  && (length($url) > 11) ) {
	slowdeath("Der eingegebene URL '$url' wird von diesem Programm nich akzeptiert!");
    }
    $url = $1; # untainted

    # Create parser object
    use HTML::Parser;
    my $p = HTML::Parser->new( api_version => 3,
			       start_h => [\&start, "self, tag, attr, attrseq, text"],
			       text_h => [ \&text, "self, dtext" ],
			       end_h   => [\&end, "self, tag, text"]
			       #comment_h => [""],
			       );
    # Event handlers for HTML parser
    sub start {
	my ($self, $tag, $attr, $attrseq, $origtext) = @_;
	# Expand relative to full urls. Prepend $new_query to
	# webpage links, i.e. <a href="...">, so that linked pages
	# will be berlinified as well.
	# Applet and Object tags are currently ignored.
	
	# don't berlinify the contents of style tags
	if ($tag eq 'style') {
	    $self->{lasttag} = 1;
	    $berlinified .= $origtext;
	    return;
	}

	# handle scripts
	if ($tag eq 'script') {
	    if ( defined($attr->{'src'}) ) { # external
		$attr->{'src'} = URI->new_abs($attr->{'src'}, $p->{base});
		$berlinified .= "<$tag " . join (" ", map( $_ . qq(="$attr->{$_}"), @$attrseq)) . ">";
	    } else { # internal
		$self->{lasttag} = 1;
		$berlinified .= $origtext;
		return;
	    }
	} 
	
	# handle frames
	if ($tag eq 'frame') {
	    if (defined($attr->{'src'})) {
		$attr->{'src'} = $new_query . URI->new_abs($attr->{'src'}, $p->{base});
		$berlinified .= "<$tag " . join (" ", map( $_ . qq(="$attr->{$_}"), @$attrseq)) . ">";
		return;
	    }
	}

	# handle external style sheets
	if ($tag eq 'link') {
	    if (defined($attr->{'href'})) {
		$attr->{'href'} = URI->new_abs($attr->{'href'}, $p->{base});
		$berlinified .= "<$tag " . join (" ", map( $_ . qq(="$attr->{$_}"), @$attrseq)) . ">";
		return;
	    }
	}
	
	# handle links, images 
	if ($tag eq 'a' || $tag eq 'img' || $tag eq 'area') {
	    if ( defined($attr->{'href'}) && $attr->{'href'} !~ /^\s*mailto/ ) { # skip links to email addresses
		$attr->{'href'} = $new_query . URI->new_abs($attr->{'href'}, $p->{base});		    
	    } elsif (defined($attr->{'src'})) {
		$attr->{'src'} = URI->new_abs($attr->{'src'}, $p->{base});
	    }
	    $berlinified .= "<$tag " . join (" ", map( $_ . qq(="$attr->{$_}"), @$attrseq)) . ">";
	    return;
	} # if ($tag eq 'a' || $tag eq 'img' || $tag eq 'area')
	
        # all other tags
	else {
	    $berlinified .= $origtext;
	    return;
	}
    } # sub start

    sub text {
	my ($self, $text) = @_;
	if (defined($self->{lasttag})) {
	    $berlinified .= $text;
	    return;
	}
	$berlinified .= substitute($text);
    }

    sub end {
	my ($self, $tag, $origtext) = @_;
	$berlinified .= $origtext;
	if ($tag =~ m/style|script/) {
	    $self->{lasttag} = undef;
	}
    }

    # Get document and base url
    use LWP;
    my $doc;
    my $ua = LWP::UserAgent->new();
    my $request = HTTP::Request->new(GET => $url);
    my $response = $ua->request($request);
    if ($response->is_success) {
	$p->{base} = $response->base();
	$doc = $response->content();
    } else { slowdeath("Das Dokument '$url' konnte nicht heruntergeladen werden!"); }
    
    # Parse HTML
    $p->parse($doc);
    $p->eof(); # Clear buffer

    print $q->header();
    print $berlinified;
} # if ($q->param())

# print HTML form
else {
    my $title = 'Berlinifyer';
    print $q->header(),$q->start_html( {'title'=>$title,'author'=>'Ramiro G&oacute;mez'} );
    print $q->p('Hier k&ouml;nnen Web-Dokumente ins Berlinische übersetzt werden. Bitte geben Sie die Internetadresse, des zu übersetzenden HTML-Dokuments an.'),
    $q->start_form({'method'=>'get'}),$q->textfield({'name'=>'url',
				    'size'=>'50',
				    'maxlength'=>'100',
				    'default'=>'http://'}),$q->submit(),
    $q->end_form(),$q->end_html();
}

# "translate" to Berlin's dialect 
sub substitute {
    my $line = shift;
    my $vowel = 'aeiouäöü';
    #my $consonant = 'bcdfghjklmnpqrstvwxyz';
    
    # translate only the plural form of a word, if its case 
    # differs from the case of the translation 
    my %subst_words = ('An der' => 'Anna',
		       'an der' => 'anna',
		       'An die' => 'Anne',
		       'an die' => 'anne',
		       'Auch' => 'Och',
		       'auch' => 'och',
		       'Bäuche' => 'Plautzen',
		       'Beamten' => 'Stubenpisser',
		       'Beamter' => 'Stubenpisser',
		       'Beine' => 'Kackstelzen',
		       'Brüder' => 'Atzen',
		       'Du' => 'De',
		       'du' => 'de',
		       'Elektriker' => 'Strippenzieher',
		       'Finger' => 'Wichsgriffel',
		       'Flasche' => 'Pulle',
		       'Flaschen' => 'Pullen',
		       'Frau' => 'Butze',
		       'Frauen' => 'Butzen',
		       'Freundin' => 'Ficke',
		       'Frisur' => 'Fettpeitsche',
		       'Füße' => 'Quanten',
		       'Gesellschaft' => 'Blase',
		       'Gesichter' => 'Fratzen',
		       'Hand' => 'Pfote',
		       'Hände' => 'Wichsgriffel',
		       'Harre' => 'Peden',
		       'Herzen' => 'Cognacpumpen',
		       'Hitze' => 'Affenhitze',
		       'Hund' => 'Köter',
		       'Hunde' => 'Köter',
		       'Ich' => 'Ick',
		       'ich' => 'ick',
		       'In der' => 'Inna',
		       'in der' => 'inna',
		       'In die' => 'Inne',
		       'in die' => 'inne',
		       'Kinder' => 'Ableja',
		       'Kleidung' => 'Klamotten',
		       'Kneipe' => 'Destille',
		       'Kneipen' => 'Destillen',
		       'Lokale' => 'Destillen',
		       'Nein' => 'Nee',
		       'nein' => 'nee',
		       'Nichts' => 'Nischt',
		       'nichts' => 'nischt',
		       'Münder' => 'Futtaluken',
		       'Mutter' => 'Olle',
		       'Parfum' => 'Eau de Mief',
		       'Polizei' => 'Polente',
		       'Polizist' => 'Bulle',
		       'Polizisten' => 'Bullen',
		       'Rollstuhl' => 'AOK-Choppa',
		       'Rollstühle' => 'AOK-Choppa',
		       'Schwester' => 'Atze',
		       'Schwestern' => 'Atzen',
		       'Vater' => 'Oller',
		       'Verwandtschaft' => 'Blase',
		       'Was' => 'Wat',
		       'was' => 'wat',
		       'Wirtshäuser' => 'Destillen',
		       'Zigarette' => 'Zippe',
		       'Zigaretten' => 'Zippen');

    # substitute all keys of %subst_words with the corresponding values
    map ($line =~ s/(\b)$_(\b)/$1$subst_words{$_}$2/g, keys %subst_words);
    
    $line =~ s|(\b)Auf|$1Uff|g;
    $line =~ s|(\b)auf|$1uff|g;
    $line =~ s|(\w{2,})er([^$vowel])|$1a$2|g;
    $line =~ s|([$vowel])r([^$vowel])|$1a$2|g;
    $line =~ s|([$vowel])hr(\b)|$1a$2|g;
    $line =~ s|([^n])g([r$vowel])|$1j$2|g;
    $line =~ s/([^$vowel][^n])g(\b)/$1ch$2/g;
    $line =~ s|(\b)g([^l])|$1j$2|g;
    $line =~ s|(\b)G([^l])|$1J$2|g;
    
    return $line;
}

# Handle incorrect input
sub slowdeath {
    my $message = shift;
    print $q->header(),
    $q->start_html(-title=>"Fehler"),
    $q->p($message), $q->end_html();
    exit(1);
}
