//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1;
function t() {
	e = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
t();
//#endregion
//#region node_modules/svelte/src/constants.js
var n = {}, r = Symbol("uninitialized"), i = "http://www.w3.org/1999/xhtml", a = Array.isArray, o = Array.prototype.indexOf, s = Array.prototype.includes, c = Array.from, l = Object.keys, u = Object.defineProperty, d = Object.getOwnPropertyDescriptor, f = Object.getOwnPropertyDescriptors, p = Object.prototype, m = Array.prototype, h = Object.getPrototypeOf, g = Object.isExtensible, _ = () => {};
function v(e) {
	return e();
}
function y(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function b() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var x = 1024, S = 2048, C = 4096, w = 8192, ee = 16384, te = 32768, ne = 1 << 25, re = 65536, ie = 1 << 19, ae = 1 << 20, oe = 1 << 25, se = 65536, ce = 1 << 21, le = 1 << 22, ue = 1 << 23, de = Symbol("$state"), fe = Symbol("legacy props"), pe = Symbol(""), me = Symbol("attributes"), he = Symbol("class"), ge = Symbol("style"), _e = Symbol("text"), ve = Symbol("form reset"), ye = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), be = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function xe(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function Se() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Ce(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function we(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Te() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Ee(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function De() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Oe() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function ke(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Ae() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function je() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Me() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Ne() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Pe() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Fe(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Ie() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var T = !1;
function Le(e) {
	T = e;
}
var E;
function D(e) {
	if (e === null) throw Fe(), n;
	return E = e;
}
function Re() {
	return D(/* @__PURE__ */ L(E));
}
function O(e) {
	if (T) {
		if (/* @__PURE__ */ L(E) !== null) throw Fe(), n;
		E = e;
	}
}
function ze(e = 1) {
	if (T) {
		for (var t = e, n = E; t--;) n = /* @__PURE__ */ L(n);
		E = n;
	}
}
function Be(e = !0) {
	for (var t = 0, n = E;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ L(n);
		e && n.remove(), n = i;
	}
}
function Ve(e) {
	if (!e || e.nodeType !== 8) throw Fe(), n;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function He(e) {
	return e === this.v;
}
function Ue(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function We(e) {
	return !Ue(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var k = null;
function Ge(e) {
	k = e;
}
function Ke(t, n = !1, r) {
	k = {
		p: k,
		i: !1,
		c: null,
		e: null,
		s: t,
		x: null,
		r: K,
		l: e && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function qe(e) {
	var t = k, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) _n(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, k = t.p, e ?? {};
}
function Je() {
	return !e || k !== null && k.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Ye = [];
function Xe() {
	var e = Ye;
	Ye = [], y(e);
}
function A(e) {
	if (Ye.length === 0 && !At) {
		var t = Ye;
		queueMicrotask(() => {
			t === Ye && Xe();
		});
	}
	Ye.push(e);
}
function Ze() {
	for (; Ye.length > 0;) Xe();
}
function Qe(e) {
	var t = K;
	if (t === null) return U.f |= ue, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	$e(e, t);
}
function $e(e, t) {
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var et = ~(S | C | x);
function j(e, t) {
	e.f = e.f & et | t;
}
function tt(e) {
	e.f & 512 || e.deps === null ? j(e, x) : j(e, C);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function nt(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= se, nt(t.deps));
}
function rt(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), nt(e.deps), j(e, x);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var it = !1;
function at(e) {
	var t = it;
	try {
		return it = !1, [e(), it];
	} finally {
		it = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var ot = !1;
function st() {
	ot || (ot = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ve]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function ct(e) {
	var t = U, n = K;
	G(null), Bn(null);
	try {
		return e();
	} finally {
		G(t), Bn(n);
	}
}
function lt(e, t, n, r = n) {
	e.addEventListener(t, () => ct(n));
	let i = e[ve];
	e[ve] = i ? () => {
		i(), r(!0);
	} : () => r(!0), st();
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function ut(e) {
	let t = 0, n = qt(0), r;
	return () => {
		mn() && (X(n), Cn(() => (t === 0 && (r = Z(() => e(() => Zt(n)))), t += 1, () => {
			A(() => {
				--t, t === 0 && (r?.(), r = void 0, Zt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var dt = re | ie;
function ft(e, t, n, r) {
	new pt(e, t, n, r);
}
var pt = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = T ? E : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = ut(() => (this.#m = qt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = K;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = K.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Tn(() => {
			if (T) {
				let e = this.#t;
				Re();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#y() : this.#g();
			} else this.#b();
		}, dt), T && (this.#e = E);
	}
	#g() {
		try {
			this.#a = V(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#v(e);
		A(r), t && (this.#s = V(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#v(e) {
		var t = !1, n = !1;
		let r = () => {
			if (t) {
				Ie();
				return;
			}
			t = !0, n && Ne(), this.#s !== null && jn(this.#s, () => {
				this.#s = null;
			}), this.#S(() => {
				this.#b();
			});
		};
		return {
			reset: r,
			invoke_onerror: () => {
				try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					$e(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = V(() => e(this.#e)), A(() => {
			var e = this.#c = document.createDocumentFragment(), t = I();
			e.append(t), this.#a = this.#S(() => V(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, jn(this.#o, () => {
				this.#o = null;
			}), this.#x(M));
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = V(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Fn(this.#a, e);
				let t = this.#n.pending;
				this.#o = V(() => t(this.#e));
			} else this.#x(M);
		} catch (e) {
			this.error(e);
		}
	}
	#x(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		rt(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#S(e) {
		var t = K, n = U, r = k;
		Bn(this.#i), G(this.#i), Ge(this.#i.ctx);
		try {
			return It.ensure(), e();
		} catch (e) {
			return Qe(e), null;
		} finally {
			Bn(t), G(n), Ge(r);
		}
	}
	#C(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#C(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#x(t), this.#o && jn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, A(() => {
			this.#d = !1, this.#m && Yt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), X(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		M?.is_fork ? (this.#a && M.skip_effect(this.#a), this.#o && M.skip_effect(this.#o), this.#s && M.skip_effect(this.#s), M.oncommit(() => {
			this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (H(this.#a), null), this.#o &&= (H(this.#o), null), this.#s &&= (H(this.#s), null), T && (D(this.#t), ze(), D(Be()));
		let t = this.#n.failed, n = (e) => {
			let { reset: n, invoke_onerror: r } = this.#v(e);
			r(), t && (this.#s = this.#S(() => {
				try {
					return V(() => {
						var r = K;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return $e(e, this.#i.parent), null;
				}
			}));
		};
		A(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				$e(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => $e(e, this.#i && this.#i.parent)) : n(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function mt(e, t, n, r) {
	let i = Je() ? vt : xt;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = K, c = ht(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				$e(e, s);
			}
			gt();
		}
	}
	var d = _t();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ bt(e))).then(u).catch((e) => $e(e, s)).finally(d);
	}
	l ? l.then(() => {
		c(), f(), gt();
	}) : f();
}
function ht() {
	var e = K, t = U, n = k, r = M;
	return function(i = !0) {
		Bn(e), G(t), Ge(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function gt(e = !0) {
	Bn(null), G(null), Ge(null), e && M?.deactivate();
}
function _t() {
	var e = K, t = e.b, n = M, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function vt(e) {
	var t = 2 | S;
	return K !== null && (K.f |= ie), {
		ctx: k,
		deps: null,
		effects: null,
		equals: He,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: r,
		wv: 0,
		parent: K,
		ac: null
	};
}
var yt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function bt(e, t, n) {
	let i = K;
	i === null && Se();
	var a = void 0, o = qt(r), s = !U, c = /* @__PURE__ */ new Set();
	return Sn(() => {
		var t = K, n = b();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== ye && n.reject(e);
			}).finally(gt);
		} catch (e) {
			n.reject(e), gt();
		}
		var r = M;
		if (s) {
			if (t.f & 32768) var l = _t();
			if (i.b?.is_rendered()) r.async_deriveds.get(t)?.reject(yt);
			else for (let e of c.values()) e.reject(yt);
			c.add(n), r.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== yt && (r.activate(), t ? (o.f |= ue, Yt(o, t)) : (o.f & 8388608 && (o.f ^= ue), Yt(o, e)), r.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), hn(() => {
		for (let e of c) e.reject(yt);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/*#__NO_SIDE_EFFECTS__*/
function xt(e) {
	let t = /* @__PURE__ */ vt(e);
	return t.equals = We, t;
}
function St(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) H(t[n]);
	}
}
function Ct(e) {
	var t, n = K, i = e.parent;
	if (!Rn && i !== null && e.v !== r && i.f & 24576) return Pe(), e.v;
	Bn(i);
	try {
		e.f &= ~se, St(e), t = Zn(e);
	} finally {
		Bn(n);
	}
	return t;
}
function wt(e) {
	var t = Ct(e);
	if (!e.equals(t) && (e.wv = Jn(), (!M?.is_fork || e.deps === null) && (M === null ? e.v = t : (M.capture(e, t, !0), Ot?.capture(e, t, !0)), e.deps === null))) {
		j(e, x);
		return;
	}
	Rn || (N === null ? tt(e) : (mn() || M?.is_fork) && N.set(e, t));
}
function Tt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && ct(() => {
		t.ac.abort(ye), t.ac = null;
	}), t.fn !== null && (t.teardown = _), $n(t, 0), Dn(t));
}
function Et(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && er(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var Dt = null, M = null, Ot = null, N = null, kt = null, At = !1, jt = !1, Mt = null, Nt = null, Pt = 0, Ft = 1, It = class e {
	id = Ft++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = 0;
	#o = /* @__PURE__ */ new Map();
	#s = null;
	#c = [];
	#l = [];
	#u = /* @__PURE__ */ new Set();
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Map();
	#p = /* @__PURE__ */ new Set();
	is_fork = !1;
	#m = !1;
	constructor() {
		Dt === null ? Dt = this : (Dt.#n = this, this.#t = Dt), Dt = this;
	}
	#h() {
		if (this.is_fork) return !0;
		for (let n of this.#o.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#f.has(e)) {
					t = !0;
					break;
				}
				e = e.parent;
			}
			if (!t) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#f.has(e) || this.#f.set(e, {
			d: [],
			m: []
		}), this.#p.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#f.get(e);
		if (n) {
			this.#f.delete(e);
			for (var r of n.d) j(r, S), t(r);
			for (r of n.m) j(r, C), t(r);
		}
		this.#p.add(e);
	}
	#g() {
		this.#e = !0, Pt++ > 1e3 && (this.#x(), Rt());
		for (let e of this.#u) this.#d.delete(e), j(e, S), this.schedule(e);
		for (let e of this.#d) j(e, C), this.schedule(e);
		let t = this.#c;
		this.#c = [], this.apply();
		var n = Mt = [], r = [], i = Nt = [];
		for (let e of t) try {
			this.#_(e, n, r);
		} catch (t) {
			throw Ut(e), this.#h() || this.discard(), t;
		}
		if (M = null, i.length > 0) {
			var a = e.ensure();
			for (let e of i) a.schedule(e);
		}
		if (Mt = null, Nt = null, this.#h()) {
			this.#b(r), this.#b(n);
			for (let [e, t] of this.#f) Ht(e, t);
			i.length > 0 && M.#g();
			return;
		}
		let o = this.#v();
		if (o) {
			this.#b(r), this.#b(n), o.#y(this);
			return;
		}
		this.#u.clear(), this.#d.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), Ot = this, Bt(r), Bt(n), Ot = null, this.#s?.resolve();
		var s = M;
		if (this.#a === 0 && (this.#c.length === 0 || s !== null) && this.#x(), this.#c.length > 0) {
			if (s !== null) {
				let e = s;
				e.#c.push(...this.#c.filter((t) => !e.#c.includes(t)));
			} else s = this;
		}
		s !== null && s.#g();
	}
	#_(e, t, n) {
		e.f ^= x;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#f.has(r)) && r.fn !== null) {
				a ? r.f ^= x : i & 4 ? t.push(r) : Yn(r) && (i & 16 && this.#d.add(r), er(r));
				var o = r.first;
				if (o !== null) {
					r = o;
					continue;
				}
			}
			for (; r !== null;) {
				var s = r.next;
				if (s !== null) {
					r = s;
					break;
				}
				r = r.parent;
			}
		}
	}
	#v() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#y(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve).catch(e.reject);
		}
		e.async_deriveds.clear(), this.transfer_effects(e.#u, e.#d);
		let t = (e) => {
			var n = e.reactions;
			if (n !== null && !(e.f & 2 && !(e.f & 6144))) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#d.delete(i), j(i, S), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#x(), M = this, this.#g();
	}
	#b(e) {
		for (var t = 0; t < e.length; t += 1) rt(e[t], this.#u, this.#d);
	}
	capture(e, t, n = !1) {
		e.v !== r && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), N?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		M = this;
	}
	deactivate() {
		M = null, N = null;
	}
	flush() {
		try {
			jt = !0, M = this, this.#g();
		} finally {
			Pt = 0, kt = null, Mt = null, Nt = null, jt = !1, M = null, N = null, Gt.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear();
		for (let e of this.async_deriveds.values()) e.reject(yt);
		this.#x(), this.#s?.resolve();
	}
	register_created_effect(e) {
		this.#l.push(e);
	}
	increment(e, t) {
		if (this.#a += 1, e) {
			let e = this.#o.get(t) ?? 0;
			this.#o.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#a, e) {
			let e = this.#o.get(t) ?? 0;
			e === 1 ? this.#o.delete(t) : this.#o.set(t, e - 1);
		}
		this.#m || (this.#m = !0, A(() => {
			this.#m = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#u.add(t);
		for (let e of t) this.#d.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	settled() {
		return (this.#s ??= b()).promise;
	}
	static ensure() {
		if (M === null) {
			let t = M = new e();
			!jt && !At && A(() => {
				t.#e || t.flush();
			});
		}
		return M;
	}
	apply() {
		N = null;
	}
	schedule(e) {
		if (kt = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768)) {
			e.b.defer_effect(e);
			return;
		}
		for (var t = e; t.parent !== null;) {
			t = t.parent;
			var n = t.f;
			if (Mt !== null && t === K && (U === null || !(U.f & 2))) return;
			if (n & 96) {
				if (!(n & 1024)) return;
				t.f ^= x;
			}
		}
		this.#c.push(t);
	}
	#x() {
		if (this.linked) {
			var e = this.#t, t = this.#n;
			e === null || (e.#n = t), t === null ? Dt = e : t.#t = e, this.linked = !1;
		}
	}
};
function Lt(e) {
	var t = At;
	At = !0;
	try {
		var n;
		for (e && (M !== null && !M.is_fork && M.flush(), n = e());;) {
			if (Ze(), M === null) return n;
			M.flush();
		}
	} finally {
		At = t;
	}
}
function Rt() {
	try {
		De();
	} catch (e) {
		$e(e, kt);
	}
}
var zt = null;
function Bt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Yn(r) && (zt = /* @__PURE__ */ new Set(), er(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && An(r), zt?.size > 0)) {
				Gt.clear();
				for (let e of zt) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) zt.has(n) && (zt.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || er(n);
					}
				}
				zt.clear();
			}
		}
		zt = null;
	}
}
function Vt(e) {
	M.schedule(e);
}
function Ht(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), j(e, x);
		for (var n = e.first; n !== null;) Ht(n, t), n = n.next;
	}
}
function Ut(e) {
	j(e, x);
	for (var t = e.first; t !== null;) Ut(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Wt = /* @__PURE__ */ new Set(), Gt = /* @__PURE__ */ new Map(), Kt = !1;
function qt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: He,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Jt(e, t) {
	let n = qt(e, t);
	return Hn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function P(t, n = !1, r = !0) {
	let i = qt(t);
	return n || (i.equals = We), e && r && k !== null && k.l !== null && (k.l.s ??= []).push(i), i;
}
function F(e, t, n = !1) {
	return U !== null && (!W || U.f & 131072) && Je() && U.f & 4325394 && (Vn === null || !Vn.has(e)) && Me(), Yt(e, n ? $t(t) : t, Nt);
}
function Yt(e, t, n = null) {
	if (!e.equals(t)) {
		Gt.set(e, Rn ? t : e.v);
		var r = It.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Ct(t), N === null && tt(t);
		}
		e.wv = Jn(), Qt(e, S, n), Je() && K !== null && K.f & 1024 && !(K.f & 96) && (Y === null ? Un([e]) : Y.push(e)), !r.is_fork && Wt.size > 0 && !Kt && Xt();
	}
	return t;
}
function Xt() {
	Kt = !1;
	for (let e of Wt) {
		e.f & 1024 && j(e, C);
		let t;
		try {
			t = Yn(e);
		} catch {
			t = !0;
		}
		t && er(e);
	}
	Wt.clear();
}
function Zt(e) {
	F(e, e.v + 1);
}
function Qt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Je(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === K)) {
			var l = (c & S) === 0;
			if (l && j(s, t), c & 131072) Wt.add(s);
			else if (c & 2) {
				var u = s;
				N?.delete(u), c & 65536 || (c & 512 && (K === null || !(K.f & 2097152)) && (s.f |= se), Qt(u, C, n));
			} else if (l) {
				var d = s;
				c & 16 && zt !== null && zt.add(d), n === null ? Vt(d) : n.push(d);
			}
		}
	}
}
function $t(e) {
	if (typeof e != "object" || !e || de in e) return e;
	let t = h(e);
	if (t !== p && t !== m) return e;
	var n = /* @__PURE__ */ new Map(), i = a(e), o = /* @__PURE__ */ Jt(0), s = null, c = Kn, l = (e) => {
		if (Kn === c) return e();
		var t = U, n = Kn;
		G(null), qn(c);
		var r = e();
		return G(t), qn(n), r;
	};
	return i && n.set("length", /* @__PURE__ */ Jt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Ae();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Jt(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var i = n.get(t);
			if (i === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Jt(r, s));
					n.set(t, e), Zt(o);
				}
			} else F(i, r), Zt(o);
			return !0;
		},
		get(t, i, a) {
			if (i === de) return e;
			var o = n.get(i), c = i in t;
			if (o === void 0 && (!c || d(t, i)?.writable) && (o = l(() => /* @__PURE__ */ Jt($t(c ? t[i] : r), s)), n.set(i, o)), o !== void 0) {
				var u = X(o);
				return u === r ? void 0 : u;
			}
			return Reflect.get(t, i, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var i = Reflect.getOwnPropertyDescriptor(e, t);
			if (i && "value" in i) {
				var a = n.get(t);
				a && (i.value = X(a));
			} else if (i === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== r) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return i;
		},
		has(e, t) {
			if (t === de) return !0;
			var i = n.get(t), a = i !== void 0 && i.v !== r || Reflect.has(e, t);
			return (i !== void 0 || K !== null && (!a || d(e, t)?.writable)) && (i === void 0 && (i = l(() => /* @__PURE__ */ Jt(a ? $t(e[t]) : r, s)), n.set(t, i)), X(i) === r) ? !1 : a;
		},
		set(e, t, a, c) {
			var u = n.get(t), f = t in e;
			if (i && t === "length") for (var p = a; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Jt(r, s)), n.set(p + "", m)) : F(m, r);
			}
			if (u === void 0) (!f || d(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Jt(void 0, s)), F(u, $t(a)), n.set(t, u));
			else {
				f = u.v !== r;
				var h = l(() => $t(a));
				F(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, a), !f) {
				if (i && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && F(_, v + 1);
				}
				Zt(o);
			}
			return !0;
		},
		ownKeys(e) {
			X(o);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== r;
			});
			for (var [i, a] of n) a.v !== r && !(i in e) && t.push(i);
			return t;
		},
		setPrototypeOf() {
			je();
		}
	});
}
var en, tn, nn, rn;
function an() {
	if (en === void 0) {
		en = window, tn = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		nn = d(t, "firstChild").get, rn = d(t, "nextSibling").get, g(e) && (e[he] = void 0, e[me] = null, e[ge] = void 0, e.__e = void 0), g(n) && (n[_e] = void 0);
	}
}
function I(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function on(e) {
	return nn.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function L(e) {
	return rn.call(e);
}
function R(e, t) {
	if (!T) return /* @__PURE__ */ on(e);
	var n = /* @__PURE__ */ on(E);
	if (n === null) n = E.appendChild(I());
	else if (t && n.nodeType !== 3) {
		var r = I();
		return n?.before(r), D(r), r;
	}
	return t && dn(n), D(n), n;
}
function sn(e, t = !1) {
	if (!T) {
		var n = /* @__PURE__ */ on(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ L(n) : n;
	}
	if (t) {
		if (E?.nodeType !== 3) {
			var r = I();
			return E?.before(r), D(r), r;
		}
		dn(E);
	}
	return E;
}
function z(e, t = 1, n = !1) {
	let r = T ? E : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ L(r);
	if (!T) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = I();
			return r === null ? i?.after(a) : r.before(a), D(a), a;
		}
		dn(r);
	}
	return D(r), r;
}
function cn(e) {
	e.textContent = "";
}
function ln() {
	return !1;
}
function un(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function dn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function fn(e) {
	K === null && (U === null && Ee(e), Te()), Rn && we(e);
}
function pn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function B(e, t) {
	var n = K;
	n !== null && n.f & 8192 && (e |= w);
	var r = {
		ctx: k,
		deps: null,
		nodes: null,
		f: e | S | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	M?.register_created_effect(r);
	var i = r;
	if (e & 4) Mt === null ? It.ensure().schedule(r) : Mt.push(r);
	else if (t !== null) {
		try {
			er(r);
		} catch (e) {
			throw H(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= re));
	}
	if (i !== null && (i.parent = n, n !== null && pn(i, n), U !== null && U.f & 2 && !(e & 64))) {
		var a = U;
		(a.effects ??= []).push(i);
	}
	return r;
}
function mn() {
	return U !== null && !W;
}
function hn(e) {
	let t = B(8, null);
	return j(t, x), t.teardown = e, t;
}
function gn(e) {
	fn("$effect");
	var t = K.f;
	if (!U && t & 32 && k !== null && !k.i) {
		var n = k;
		(n.e ??= []).push(e);
	} else return _n(e);
}
function _n(e) {
	return B(4 | ae, e);
}
function vn(e) {
	return fn("$effect.pre"), B(8 | ae, e);
}
function yn(e) {
	It.ensure();
	let t = B(64 | ie, e);
	return () => {
		H(t);
	};
}
function bn(e) {
	It.ensure();
	let t = B(64 | ie, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? jn(t, () => {
			H(t), n(void 0);
		}) : (H(t), n(void 0));
	});
}
function xn(e) {
	return B(4, e);
}
function Sn(e) {
	return B(le | ie, e);
}
function Cn(e, t = 0) {
	return B(8 | t, e);
}
function wn(e, t = [], n = [], r = []) {
	mt(r, t, n, (t) => {
		B(8, () => {
			e(...t.map(X));
		});
	});
}
function Tn(e, t = 0) {
	return B(16 | t, e);
}
function V(e) {
	return B(32 | ie, e);
}
function En(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = Rn, n = U;
		zn(!0), G(null);
		try {
			t.call(null);
		} finally {
			zn(e), G(n);
		}
	}
}
function Dn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && ct(() => {
			e.abort(ye);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : H(n, t), n = r;
	}
}
function On(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || H(t), t = n;
	}
}
function H(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (kn(e.nodes.start, e.nodes.end), n = !0), e.f |= ne, Dn(e, t && !n), $n(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	En(e), e.f ^= ne, e.f |= ee;
	var i = e.parent;
	i !== null && i.first !== null && An(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function kn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ L(e);
		e.remove(), e = n;
	}
}
function An(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function jn(e, t, n = !0) {
	var r = [];
	Mn(e, r, !0);
	var i = () => {
		n && H(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Mn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= w;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = !!(i.f & 65536) || !!(i.f & 32) && !!(e.f & 16);
				Mn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Nn(e) {
	Pn(e, !0);
}
function Pn(e, t) {
	if (e.f & 8192) {
		e.f ^= w, e.f & 1024 || (j(e, S), It.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = !!(n.f & 65536) || !!(n.f & 32);
			Pn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Fn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ L(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var In = null, Ln = !1, Rn = !1;
function zn(e) {
	Rn = e;
}
var U = null, W = !1;
function G(e) {
	U = e;
}
var K = null;
function Bn(e) {
	K = e;
}
var Vn = null;
function Hn(e) {
	U !== null && (Vn ??= /* @__PURE__ */ new Set()).add(e);
}
var q = null, J = 0, Y = null;
function Un(e) {
	Y = e;
}
var Wn = 1, Gn = 0, Kn = Gn;
function qn(e) {
	Kn = e;
}
function Jn() {
	return ++Wn;
}
function Yn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~se), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Yn(a) && wt(a), a.wv > e.wv) return !0;
		}
		t & 512 && N === null && j(e, x);
	}
	return !1;
}
function Xn(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(Vn !== null && Vn.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? Xn(a, t, !1) : t === a && (n ? j(a, S) : a.f & 1024 && j(a, C), Vt(a));
	}
}
function Zn(e) {
	var t = q, n = J, r = Y, i = U, a = Vn, o = k, s = W, c = Kn, l = e.f;
	q = null, J = 0, Y = null, U = l & 96 ? null : e, Vn = null, Ge(e.ctx), W = !1, Kn = ++Gn, e.ac !== null && (ct(() => {
		e.ac.abort(ye);
	}), e.ac = null);
	try {
		e.f |= ce;
		var u = e.fn, d = u();
		e.f |= te;
		var f = e.deps, p = M?.is_fork;
		if (q !== null) {
			var m;
			if (p || $n(e, J), f !== null && J > 0) for (f.length = J + q.length, m = 0; m < q.length; m++) f[J + m] = q[m];
			else e.deps = f = q;
			if (mn() && e.f & 512) for (m = J; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && J < f.length && ($n(e, J), f.length = J);
		if (Je() && Y !== null && !W && f !== null && !(e.f & 6146)) for (m = 0; m < Y.length; m++) Xn(Y[m], e);
		if (i !== null && i !== e) {
			if (Gn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Gn;
			if (t !== null) for (let e of t) e.rv = Gn;
			Y !== null && (r === null ? r = Y : r.push(...Y));
		}
		return e.f & 8388608 && (e.f ^= ue), d;
	} catch (e) {
		return Qe(e);
	} finally {
		e.f ^= ce, q = t, J = n, Y = r, U = i, Vn = a, Ge(o), W = s, Kn = c;
	}
}
function Qn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var i = o.call(n, e);
		if (i !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[i] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (q === null || !s.call(q, t))) {
		var c = t;
		c.f & 512 && (c.f ^= 512, c.f &= ~se), c.v !== r && tt(c), c.ac !== null && ct(() => {
			c.ac.abort(ye), c.ac = null, j(c, S);
		}), Tt(c), $n(c, 0);
	}
}
function $n(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Qn(e, n[r]);
}
function er(e) {
	var t = e.f;
	if (!(t & 16384)) {
		j(e, x);
		var n = K, r = Ln;
		K = e, Ln = !(t & 96);
		try {
			t & 16777232 ? On(e) : Dn(e), En(e);
			var i = Zn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Wn;
		} finally {
			Ln = r, K = n;
		}
	}
}
async function tr() {
	await Promise.resolve(), Lt();
}
function X(e) {
	var t = !!(e.f & 2);
	if (In?.add(e), U !== null && !W && !(K !== null && K.f & 16384) && (Vn === null || !Vn.has(e))) {
		var n = U.deps;
		if (U.f & 2097152) e.rv < Gn && (e.rv = Gn, q === null && n !== null && n[J] === e ? J++ : q === null ? q = [e] : q.push(e));
		else {
			U.deps ??= [], s.call(U.deps, e) || U.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [U] : s.call(r, U) || r.push(U);
		}
	}
	if (Rn && Gt.has(e)) return Gt.get(e);
	if (t) {
		var i = e;
		if (Rn) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || rr(i)) && (a = Ct(i)), Gt.set(i, a), a;
		}
		var o = !(i.f & 512) && !W && U !== null && (Ln || !!(U.f & 512)), c = (i.f & te) === 0;
		Yn(i) && (o && (i.f |= 512), wt(i)), o && !c && (Et(i), nr(i));
	}
	if (N?.has(e)) return N.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function nr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Et(t), nr(t));
}
function rr(e) {
	if (e.v === r) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Gt.has(t) || t.f & 2 && rr(t)) return !0;
	return !1;
}
function Z(e) {
	var t = W;
	try {
		return W = !0, e();
	} finally {
		W = t;
	}
}
function ir(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (de in e) ar(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && de in n && ar(n);
		}
	}
}
function ar(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			ar(e[n], t);
		} catch {}
		let n = h(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = f(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var or = Symbol("events"), sr = /* @__PURE__ */ new Set(), cr = /* @__PURE__ */ new Set();
function lr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || fr.call(t, e), !e.cancelBubble) return ct(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? A(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function ur(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = lr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && hn(() => {
		t.removeEventListener(e, o, a);
	});
}
var dr = null;
function fr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	dr = e;
	var o = 0, s = dr === e && e[or];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[or] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		u(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var d = U, f = K;
		G(null), Bn(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[or]?.[r];
					h != null && (!a.disabled || e.target === a) && h.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble) break;
				o++, a = o < i.length ? i[o] : null;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[or] = t, delete e.currentTarget, G(d), Bn(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var pr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function mr(e) {
	return pr?.createHTML(e) ?? e;
}
function hr(e) {
	var t = un("template");
	return t.innerHTML = mr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function gr(e, t) {
	var n = K;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Q(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (T) return gr(E, null), E;
		i === void 0 && (i = hr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ on(i)));
		var t = r || tn ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ on(t), s = t.lastChild;
			gr(o, s);
		} else gr(t, t);
		return t;
	};
}
function $(e, t) {
	if (T) {
		var n = K;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = E), Re();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var _r = ["touchstart", "touchmove"];
function vr(e) {
	return _r.includes(e);
}
function yr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[_e] ??= e.nodeValue) && (e[_e] = n, e.nodeValue = `${n}`);
}
function br(e, t) {
	return Cr(e, t);
}
function xr(e, t) {
	an(), t.intro = t.intro ?? !1;
	let r = t.target, i = T, a = E;
	try {
		for (var o = /* @__PURE__ */ on(r); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ L(o);
		if (!o) throw n;
		Le(!0), D(o);
		let i = Cr(e, {
			...t,
			anchor: o
		});
		return Le(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== n && console.warn("Failed to hydrate: ", i), t.recover === !1 && Oe(), an(), cn(r), Le(!1), br(e, t);
	} finally {
		Le(i), D(a);
	}
}
var Sr = /* @__PURE__ */ new Map();
function Cr(e, { target: t, anchor: r, props: i = {}, events: a, context: o, intro: s = !0, transformError: l }) {
	an();
	var u = void 0, d = bn(() => {
		var s = r ?? t.appendChild(I());
		ft(s, { pending: () => {} }, (t) => {
			Ke({});
			var r = k;
			if (o && (r.c = o), a && (i.$$events = a), T && gr(t, null), u = e(t, i) || {}, T && (K.nodes.end = E, E === null || E.nodeType !== 8 || E.data !== "]")) throw Fe(), n;
			qe();
		}, l);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = vr(r);
					for (let e of [t, document]) {
						var a = Sr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), Sr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, fr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(c(sr)), cr.add(f), () => {
			for (var e of d) for (let r of [t, document]) {
				var n = Sr.get(r), i = n.get(e);
				--i == 0 ? (r.removeEventListener(e, fr), n.delete(e), n.size === 0 && Sr.delete(r)) : n.set(e, i);
			}
			cr.delete(f), s !== r && s.parentNode?.removeChild(s);
		};
	});
	return wr.set(u, d), u;
}
var wr = /* @__PURE__ */ new WeakMap();
function Tr(e, t) {
	let n = wr.get(e);
	return n ? (wr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Er = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) Nn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (Nn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (H(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Fn(r, t), t.append(I()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else H(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), jn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (H(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = M, r = ln();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = I();
				i.append(a), this.#n.set(e, {
					effect: V(() => t(a)),
					fragment: i
				});
			} else this.#t.set(e, V(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else T && (this.anchor = E), this.#a(n);
	}
};
function Dr(t) {
	k === null && xe("onMount"), e && k.l !== null ? Or(k).m.push(t) : gn(() => {
		let e = Z(t);
		if (typeof e == "function") return e;
	});
}
function Or(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function kr(e, t, n = !1) {
	var r;
	T && (r = E, Re());
	var i = new Er(e), a = n ? re : 0;
	function o(e, t) {
		if (T) {
			var n = Ve(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Be();
				D(a), i.anchor = a, Le(!1), i.ensure(e, t), Le(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	Tn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/each.js
function Ar(e, t) {
	return t;
}
function jr(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		jn(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Mr(e, c(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var l = r.length === 0 && n !== null;
		if (l) {
			var u = n, d = u.parentNode;
			cn(d), d.append(u), e.items.clear();
		}
		Mr(e, t, !l);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Mr(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= oe, Fn(a, document.createDocumentFragment())) : H(t[i], n);
	}
}
var Nr;
function Pr(e, t, n, r, i, o = null) {
	var s = e, l = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = T ? D(/* @__PURE__ */ on(u)) : u.appendChild(I());
	}
	T && Re();
	var d = null, f = /* @__PURE__ */ xt(() => {
		var e = n();
		return a(e) ? e : e == null ? [] : c(e);
	}), p, m = /* @__PURE__ */ new Map(), h = !0;
	function g(e) {
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, Ir(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= oe, Rr(d, null, s)) : Nn(d) : jn(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: Tn(() => {
			p = X(f);
			var e = p.length;
			let a = !1;
			T && Ve(s) === "[!" != (e === 0) && (s = Be(), D(s), Le(!1), a = !0);
			for (var c = /* @__PURE__ */ new Set(), u = M, v = ln(), y = 0; y < e; y += 1) {
				T && E.nodeType === 8 && E.data === "]" && (s = E, a = !0, Le(!1));
				var b = p[y], x = r(b, y), S = h ? null : l.get(x);
				S ? (S.v && Yt(S.v, b), S.i && Yt(S.i, y), v && u.unskip_effect(S.e)) : (S = Lr(l, h ? s : Nr ??= I(), b, x, y, i, t, n), h || (S.e.f |= oe), l.set(x, S)), c.add(x);
			}
			if (e === 0 && o && !d && (h ? d = V(() => o(s)) : (d = V(() => o(Nr ??= I())), d.f |= oe)), e > c.size && Ce("", "", ""), T && e > 0 && D(Be()), !h) {
				if (m.set(u, c), v) {
					for (let [e, t] of l) c.has(e) || u.skip_effect(t.e);
					u.oncommit(g), u.ondiscard(_);
				} else g(u);
			}
			a && Le(!0), X(f);
		}),
		flags: t,
		items: l,
		pending: m,
		outrogroups: null,
		fallback: d
	};
	h = !1, T && (s = E);
}
function Fr(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function Ir(e, t, n, r, i) {
	var a = !!(r & 8), o = t.length, s = e.items, l = Fr(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (Nn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) {
			if (_.f ^= oe, _ === l) Rr(_, null, n);
			else {
				var y = d ? d.next : l;
				_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), zr(e, d, _), zr(e, _, y), Rr(_, y, n), d = _, p = [], m = [], l = Fr(d.next);
				continue;
			}
		}
		if (_ !== l) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) Rr(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					zr(e, S.prev, C.next), zr(e, d, S), zr(e, C, b), l = b, d = C, --v, p = [], m = [];
				} else u.delete(_), Rr(_, l, n), zr(e, _.prev, _.next), zr(e, _, d === null ? e.effect.first : d.next), zr(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; l !== null && l !== _;) (u ??= /* @__PURE__ */ new Set()).add(l), m.push(l), l = Fr(l.next);
			if (l === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, l = Fr(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Mr(e, c(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (l !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; l !== null;) !(l.f & 8192) && l !== e.fallback && w.push(l), l = Fr(l.next);
		var ee = w.length;
		if (ee > 0) {
			var te = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.fix();
			}
			jr(e, w, te);
		}
	}
	a && A(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function Lr(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? qt(n) : /* @__PURE__ */ P(n, !1, !1) : null, l = o & 2 ? qt(i) : null;
	return {
		v: c,
		i: l,
		e: V(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Rr(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ L(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function zr(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Br(e, t) {
	xn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = un("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Vr = Symbol("is custom element"), Hr = Symbol("is html"), Ur = be ? "link" : "LINK";
function Wr(e) {
	if (T) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Kr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Kr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ve] = n, A(n), st();
	}
}
function Gr(e, t) {
	var n = qr(e);
	n.checked !== (n.checked = t ?? void 0) && (e.checked = t);
}
function Kr(e, t, n, r) {
	var i = qr(e);
	T && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Ur) || i[t] !== (i[t] = n) && (t === "loading" && (e[pe] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Yr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function qr(e) {
	return e[me] ??= {
		[Vr]: e.nodeName.includes("-"),
		[Hr]: e.namespaceURI === i
	};
}
var Jr = /* @__PURE__ */ new Map();
function Yr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Jr.get(t);
	if (n) return n;
	Jr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = f(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = h(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Xr(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	lt(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = Zr(e) ? Qr(a) : a, n(a), M !== null && r.add(M), await tr(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (T && e.defaultValue !== e.value || Z(t) == null && e.value) && (n(Zr(e) ? Qr(e.value) : e.value), M !== null && r.add(M)), Cn(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = M;
			if (r.has(i)) return;
		}
		Zr(e) && n === Qr(e.value) || e.type === "date" && !n && !e.value || n !== e.value && (e.value = n ?? "");
	});
}
function Zr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Qr(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function $r(e = !1) {
	let t = k, n = t.l.u;
	if (!n) return;
	let r = () => ir(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ vt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => X(i);
	}
	n.b.length && vn(() => {
		ei(t, r), y(n.b);
	}), gn(() => {
		let e = Z(() => n.m.map(v));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && gn(() => {
		ei(t, r), y(n.a);
	});
}
function ei(e, t) {
	if (e.l.s) for (let t of e.l.s) X(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function ti(t, n, r, i) {
	var a = !e || !!(r & 2), o = !!(r & 8), s = !!(r & 16), c = i, l = !0, u = void 0, f = () => s && a ? (u ??= /* @__PURE__ */ vt(i), X(u)) : (l && (l = !1, c = s ? Z(i) : i), c);
	let p;
	if (o) {
		var m = de in t || fe in t;
		p = d(t, n)?.set ?? (m && n in t ? (e) => t[n] = e : void 0);
	}
	var h, g = !1;
	o ? [h, g] = at(() => t[n]) : h = t[n], h === void 0 && i !== void 0 && (h = f(), p && (a && ke(n), p(h)));
	var _ = a ? () => {
		var e = t[n];
		return e === void 0 ? f() : (l = !0, e);
	} : () => {
		var e = t[n];
		return e !== void 0 && (c = void 0), e === void 0 ? c : e;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var v = t.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || v || g) && p(t ? _() : e), e) : _();
		});
	}
	var y = !1, b = (r & 1 ? vt : xt)(() => (y = !1, _()));
	o && X(b);
	var x = K;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? X(b) : a && o ? $t(e) : e;
			return F(b, n), y = !0, c !== void 0 && (c = n), e;
		}
		return Rn && y || x.f & 16384 ? b.v : X(b);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function ni(e) {
	return new ri(e);
}
var ri = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ P(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return X(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === fe || (X(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return F(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		});
		this.#t = (e.hydrate ? xr : br)(e.component, {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		}), (!e?.props?.$$host || e.sync === !1) && Lt(), this.#e = r.$$events;
		for (let e of Object.keys(this.#t)) e !== "$set" && e !== "$destroy" && e !== "$on" && u(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(r, e);
		}, this.#t.$destroy = () => {
			Tr(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, ii;
typeof HTMLElement == "function" && (ii = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = un("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = oi(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = ai(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = ni({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = yn(() => {
				Cn(() => {
					this.$$r = !0;
					for (let e of l(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = ai(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = ai(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return l(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function ai(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function oi(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function si(e, t, n, r, i, a) {
	let o = class extends ii {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return l(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return l(t).forEach((e) => {
		u(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = ai(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (d(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		u(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region SpotifyCard.svelte
var ci = /* @__PURE__ */ Q("<div class=\"loading-state svelte-16m7f8c\"><div class=\"spinner svelte-16m7f8c\"></div> <span>Initializing Spotify Nexus...</span></div>"), li = /* @__PURE__ */ Q("<div class=\"form-grid svelte-16m7f8c\"><div class=\"form-field svelte-16m7f8c\"><span class=\"field-label svelte-16m7f8c\">Client ID</span> <input type=\"text\" placeholder=\"Spotify Developer Client ID\" class=\"input-field svelte-16m7f8c\"/></div> <div class=\"form-field svelte-16m7f8c\"><span class=\"field-label svelte-16m7f8c\">Client Secret</span> <div class=\"password-wrapper\"><input type=\"password\" placeholder=\"Spotify Developer Client Secret\" class=\"input-field svelte-16m7f8c\"/></div></div> <div class=\"form-field svelte-16m7f8c\"><span class=\"field-label svelte-16m7f8c\">Redirect URI</span> <input type=\"text\" class=\"input-field readonly svelte-16m7f8c\" readonly=\"\" disabled=\"\"/> <span class=\"helper-text svelte-16m7f8c\">Whitelist this in Spotify Dashboard</span></div> <div class=\"actions-row svelte-16m7f8c\"><button class=\"btn-primary svelte-16m7f8c\"> </button></div></div>"), ui = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-16m7f8c\"> </button>"), di = /* @__PURE__ */ Q("<div class=\"add-account-form svelte-16m7f8c\"><div class=\"form-field svelte-16m7f8c\"><input type=\"text\" placeholder=\"e.g. My Personal Account\" class=\"input-field svelte-16m7f8c\"/></div> <div class=\"actions-row svelte-16m7f8c\"><button class=\"btn-primary svelte-16m7f8c\">Add Account</button></div></div>"), fi = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-16m7f8c\">Authenticated</span>"), pi = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-16m7f8c\">Pending Auth</span>"), mi = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-16m7f8c\">Active</span>"), hi = /* @__PURE__ */ Q("<div class=\"account-item svelte-16m7f8c\"><div class=\"account-info svelte-16m7f8c\"><div class=\"account-name svelte-16m7f8c\"> </div> <div class=\"account-badges svelte-16m7f8c\"><!> <!></div></div> <div class=\"account-actions svelte-16m7f8c\"><button class=\"link-btn svelte-16m7f8c\"> </button> <div class=\"switch-container\"><label class=\"switch svelte-16m7f8c\"><input type=\"checkbox\" class=\"svelte-16m7f8c\"/> <span class=\"slider round svelte-16m7f8c\"></span></label></div> <button class=\"btn-danger-icon svelte-16m7f8c\" title=\"Delete Account\">✕</button></div></div>"), gi = /* @__PURE__ */ Q("<div class=\"empty-accounts svelte-16m7f8c\">No Spotify accounts connected.</div>"), _i = /* @__PURE__ */ Q("<div class=\"settings-section svelte-16m7f8c\"><div class=\"section-header svelte-16m7f8c\"><h3 class=\"section-title svelte-16m7f8c\">Global Credentials</h3> <button class=\"btn-ghost svelte-16m7f8c\"> </button></div> <!></div> <hr class=\"divider svelte-16m7f8c\"/> <div class=\"settings-section svelte-16m7f8c\"><div class=\"section-header svelte-16m7f8c\"><h3 class=\"section-title svelte-16m7f8c\"> </h3> <!></div> <!> <div class=\"accounts-list svelte-16m7f8c\"></div></div>", 1), vi = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-16m7f8c\"><div class=\"card-header svelte-16m7f8c\"><div class=\"header-left svelte-16m7f8c\"><h2 class=\"card-title svelte-16m7f8c\">Spotify</h2> <span class=\"type-badge svelte-16m7f8c\">Streaming Service</span></div></div> <!></section>"), yi = {
	hash: "svelte-16m7f8c",
	code: ".plugin-card.svelte-16m7f8c {background:var(--bg-surface, #0f172a);border:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));border-radius:var(--radius, 16px);padding:28px;color:var(--text-primary, #f8fafc);font-family:\"Inter\", sans-serif;box-shadow:0 4px 24px rgba(0, 0, 0, 0.2);transition:transform 0.2s ease;}.card-header.svelte-16m7f8c {display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));}.header-left.svelte-16m7f8c {display:flex;align-items:center;gap:16px;}.card-title.svelte-16m7f8c {margin:0;font-size:22px;font-weight:800;letter-spacing:-0.02em;background:linear-gradient(135deg, #fff 0%, #a5b4fc 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}.type-badge.svelte-16m7f8c {font-size:10px;padding:4px 10px;background:rgba(20, 184, 166, 0.1);color:var(--color-primary, #14b8a6);border:1px solid rgba(20, 184, 166, 0.2);border-radius:20px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;}.settings-section.svelte-16m7f8c {margin-bottom:32px;}.section-header.svelte-16m7f8c {display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;}.section-title.svelte-16m7f8c {margin:0;font-size:14px;font-weight:700;color:var(--text-secondary, #94a3b8);text-transform:uppercase;letter-spacing:0.05em;}.form-grid.svelte-16m7f8c {display:grid;grid-template-columns:1fr;gap:20px;}\n\n  @media (min-width: 640px) {.form-grid.svelte-16m7f8c {grid-template-columns:1fr 1fr;}.actions-row.svelte-16m7f8c {grid-column:span 2;}\n  }.form-field.svelte-16m7f8c {display:flex;flex-direction:column;gap:10px;}.field-label.svelte-16m7f8c {font-size:12px;font-weight:600;color:var(--text-secondary, #94a3b8);opacity:0.8;}.input-field.svelte-16m7f8c {width:100%;padding:14px 18px;background:var(--bg-input, #1e293b);border:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));border-radius:12px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.25s cubic-bezier(0.4, 0, 0.2, 1);}.input-field.svelte-16m7f8c:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 4px rgba(20, 184, 166, 0.15);background:rgba(255, 255, 255, 0.03);}.input-field.readonly.svelte-16m7f8c {opacity:0.6;cursor:not-allowed;background:rgba(255, 255, 255, 0.02);}.helper-text.svelte-16m7f8c {font-size:11px;color:var(--text-muted, #64748b);margin-top:6px;font-style:italic;}.btn-primary.svelte-16m7f8c {padding:12px 28px;background:var(--color-primary, #14b8a6);color:#000;border:none;border-radius:12px;font-weight:700;font-size:14px;cursor:pointer;transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1);box-shadow:0 4px 12px rgba(20, 184, 166, 0.2);}.btn-primary.svelte-16m7f8c:hover:not(:disabled) {filter:brightness(1.1);transform:translateY(-2px);box-shadow:0 6px 20px rgba(20, 184, 166, 0.3);}.btn-primary.svelte-16m7f8c:active:not(:disabled) {transform:translateY(0);}.btn-primary.svelte-16m7f8c:disabled {opacity:0.4;cursor:not-allowed;box-shadow:none;}.btn-ghost.svelte-16m7f8c {padding:10px 18px;background:rgba(255, 255, 255, 0.05);border:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));color:var(--text-primary, #f8fafc);border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;transition:all 0.2s ease;}.btn-ghost.svelte-16m7f8c:hover {background:rgba(255, 255, 255, 0.1);border-color:rgba(255, 255, 255, 0.2);transform:translateY(-1px);}.divider.svelte-16m7f8c {border:none;border-top:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));margin:32px 0;opacity:0.3;}.accounts-list.svelte-16m7f8c {display:flex;flex-direction:column;gap:14px;}.account-item.svelte-16m7f8c {display:flex;justify-content:space-between;align-items:center;padding:20px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));border-radius:16px;transition:all 0.3s ease;}.account-item.svelte-16m7f8c:hover {border-color:rgba(20, 184, 166, 0.3);background:rgba(255, 255, 255, 0.05);transform:translateX(4px);}.account-info.svelte-16m7f8c {display:flex;flex-direction:column;gap:8px;}.account-name.svelte-16m7f8c {font-weight:700;font-size:16px;color:#fff;}.account-badges.svelte-16m7f8c {display:flex;gap:10px;}.status-badge.svelte-16m7f8c {font-size:10px;padding:3px 10px;border-radius:6px;font-weight:800;text-transform:uppercase;letter-spacing:0.03em;}.status-badge.success.svelte-16m7f8c {background:rgba(16, 185, 129, 0.1);color:#10b981;border:1px solid rgba(16, 185, 129, 0.2);}.status-badge.warning.svelte-16m7f8c {background:rgba(245, 158, 11, 0.1);color:#f59e0b;border:1px solid rgba(245, 158, 11, 0.2);}.status-badge.active.svelte-16m7f8c {background:rgba(20, 184, 166, 0.1);color:var(--color-primary, #14b8a6);border:1px solid rgba(20, 184, 166, 0.2);}.account-actions.svelte-16m7f8c {display:flex;gap:20px;align-items:center;}.link-btn.svelte-16m7f8c {background:none;border:none;color:var(--color-primary, #14b8a6);font-size:13px;font-weight:700;cursor:pointer;padding:0;transition:opacity 0.2s;}.link-btn.svelte-16m7f8c:hover {opacity:0.8;text-decoration:underline;}.btn-danger-icon.svelte-16m7f8c {background:rgba(239, 68, 68, 0.1);color:#ef4444;border:1px solid rgba(239, 68, 68, 0.2);width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all 0.2s ease;font-size:16px;}.btn-danger-icon.svelte-16m7f8c:hover {background:#ef4444;color:#fff;transform:rotate(90deg);}\n\n  /* Switch Component */.switch.svelte-16m7f8c {position:relative;display:inline-block;width:44px;height:24px;}.switch.svelte-16m7f8c input:where(.svelte-16m7f8c) {opacity:0;width:0;height:0;}.slider.svelte-16m7f8c {position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background-color:rgba(255, 255, 255, 0.1);transition:0.4s;border:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));}.slider.svelte-16m7f8c:before {position:absolute;content:\"\";height:18px;width:18px;left:2px;bottom:2px;background-color:#94a3b8;transition:0.4s;box-shadow:0 2px 4px rgba(0, 0, 0, 0.2);}input.svelte-16m7f8c:checked + .slider:where(.svelte-16m7f8c) {background-color:var(--color-primary, #14b8a6);border-color:var(--color-primary, #14b8a6);}input.svelte-16m7f8c:checked + .slider:where(.svelte-16m7f8c):before {transform:translateX(20px);background-color:white;}.slider.round.svelte-16m7f8c {border-radius:34px;}.slider.round.svelte-16m7f8c:before {border-radius:50%;}.loading-state.svelte-16m7f8c {display:flex;flex-direction:column;align-items:center;gap:20px;padding:60px;color:var(--text-muted, #64748b);}.spinner.svelte-16m7f8c {width:40px;height:40px;border:4px solid rgba(20, 184, 166, 0.1);border-top-color:var(--color-primary, #14b8a6);border-radius:50%;\n    animation: svelte-16m7f8c-spin 0.8s cubic-bezier(0.5, 0, 0.5, 1) infinite;}\n\n  @keyframes svelte-16m7f8c-spin {\n    to {\n      transform: rotate(360deg);\n    }\n  }.add-account-form.svelte-16m7f8c {background:rgba(255, 255, 255, 0.02);padding:20px;border-radius:16px;border:1px dashed var(--border-subtle, rgba(255, 255, 255, 0.1));margin-bottom:24px;\n    animation: svelte-16m7f8c-fadeIn 0.3s ease-out;}\n\n  @keyframes svelte-16m7f8c-fadeIn {\n    from {\n      opacity: 0;\n      transform: translateY(-10px);\n    }\n    to {\n      opacity: 1;\n      transform: translateY(0);\n    }\n  }.empty-accounts.svelte-16m7f8c {text-align:center;padding:40px;background:rgba(255, 255, 255, 0.02);border-radius:16px;border:1px dashed var(--border-subtle, rgba(255, 255, 255, 0.1));color:var(--text-muted, #64748b);font-style:italic;}"
};
function bi(e, t) {
	Ke(t, !1), Br(e, yi);
	let n = ti(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(""), i = /* @__PURE__ */ P(""), a = /* @__PURE__ */ P(""), o = /* @__PURE__ */ P([]), s = /* @__PURE__ */ P(!1), c = /* @__PURE__ */ P(""), l = /* @__PURE__ */ P(!0), u = /* @__PURE__ */ P(!1), d = /* @__PURE__ */ P(!1);
	Dr(async () => {
		n(n().replace(/\/$/, "")), await f(), await m(), !X(a) && typeof window < "u" && F(a, `${window.location.protocol}//${window.location.host}/api/oauth/callback/plugins/spotify`), F(d, !!(X(r) && X(i) && X(a) && X(o).some((e) => e.is_authenticated))), F(l, !1);
	});
	async function f() {
		try {
			let e = await (await fetch(`${n()}/settings`)).json();
			e?.settings && (F(r, e.settings.client_id || ""), F(i, e.settings.client_secret || ""), F(a, e.settings.redirect_uri || ""));
		} catch (e) {
			console.error("Failed to load Spotify settings:", e);
		}
	}
	async function p() {
		if (!X(r) || !X(i)) {
			alert("Client ID and Secret are required");
			return;
		}
		try {
			if (F(u, !0), !(await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					client_id: X(r),
					client_secret: X(i),
					redirect_uri: X(a)
				})
			})).ok) throw Error("Save failed");
			console.log("Spotify credentials saved");
		} catch (e) {
			console.error("Failed to save Spotify settings:", e), alert("Failed to save settings. Check console.");
		} finally {
			F(u, !1);
		}
	}
	async function m() {
		try {
			let e = await (await fetch(`${n()}/accounts`)).json();
			F(o, e?.accounts || []);
		} catch (e) {
			console.error("Failed to load Spotify accounts:", e), F(o, []);
		}
	}
	async function h() {
		if (X(c).trim()) {
			if (X(o).length >= 25) {
				alert("Maximum 25 accounts allowed");
				return;
			}
			try {
				if (!(await fetch(`${n()}/accounts`, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						account_name: X(c),
						display_name: X(c)
					})
				})).ok) throw Error("Add failed");
				F(c, ""), F(s, !1), await m();
			} catch (e) {
				console.error("Failed to add account:", e);
			}
		}
	}
	async function g(e, t) {
		try {
			if (!(await fetch(`${n()}/accounts/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			})).ok) throw Error("Toggle failed");
			await m();
		} catch (e) {
			console.error("Failed to toggle account:", e);
		}
	}
	async function _(e, t) {
		if (confirm(`Delete account "${t}"?`)) try {
			if (!(await fetch(`${n()}/accounts/${e}`, { method: "DELETE" })).ok) throw Error("Delete failed");
			await m();
		} catch (e) {
			console.error("Failed to delete account:", e);
		}
	}
	async function v(e) {
		if (!X(r) || !X(i)) {
			alert("Please save Client ID and Secret first.");
			return;
		}
		try {
			await p();
			let t = await (await fetch(`${n()}/auth?account_id=${e}`)).json();
			t?.auth_url && (window.open(t.auth_url, "_blank", "noopener,noreferrer"), setTimeout(() => m(), 5e3));
		} catch (e) {
			console.error("Failed to start OAuth:", e);
		}
	}
	var y = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Lt();
		}
	};
	$r();
	var b = vi(), x = z(R(b), 2), S = (e) => {
		$(e, ci());
	}, C = (e) => {
		var t = _i(), n = sn(t), l = R(n), f = z(R(l), 2), m = R(f, !0);
		O(f), O(l);
		var y = z(l, 2), b = (e) => {
			var t = li(), n = R(t), o = z(R(n), 2);
			Wr(o), O(n);
			var s = z(n, 2), c = z(R(s), 2), l = R(c);
			Wr(l), O(c), O(s);
			var d = z(s, 2), f = z(R(d), 2);
			Wr(f), ze(2), O(d);
			var m = z(d, 2), h = R(m), g = R(h, !0);
			O(h), O(m), O(t), wn(() => {
				h.disabled = X(u), yr(g, X(u) ? "Saving..." : "Save Credentials");
			}), Xr(o, () => X(r), (e) => F(r, e)), Xr(l, () => X(i), (e) => F(i, e)), Xr(f, () => X(a), (e) => F(a, e)), ur("click", h, p), $(e, t);
		};
		kr(y, (e) => {
			X(d) || e(b);
		}), O(n);
		var x = z(n, 4), S = R(x), C = R(S), w = R(C);
		O(C);
		var ee = z(C, 2), te = (e) => {
			var t = ui(), n = R(t, !0);
			O(t), wn(() => yr(n, X(s) ? "Cancel" : "+ Add Account")), ur("click", t, () => F(s, !X(s))), $(e, t);
		};
		kr(ee, (e) => {
			X(o), Z(() => X(o).length < 25) && e(te);
		}), O(S);
		var ne = z(S, 2), re = (e) => {
			var t = di(), n = R(t), r = R(n);
			Wr(r), O(n);
			var i = z(n, 2), a = R(i);
			O(i), O(t), Xr(r, () => X(c), (e) => F(c, e)), ur("keydown", r, (e) => e.key === "Enter" && h()), ur("click", a, h), $(e, t);
		};
		kr(ne, (e) => {
			X(s) && e(re);
		});
		var ie = z(ne, 2);
		Pr(ie, 5, () => X(o), Ar, (e, t) => {
			var n = hi(), r = R(n), i = R(r), a = R(i, !0);
			O(i);
			var o = z(i, 2), s = R(o), c = (e) => {
				$(e, fi());
			}, l = (e) => {
				$(e, pi());
			};
			kr(s, (e) => {
				X(t), Z(() => X(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = z(s, 2), d = (e) => {
				$(e, mi());
			};
			kr(u, (e) => {
				X(t), Z(() => X(t).is_active) && e(d);
			}), O(o), O(r);
			var f = z(r, 2), p = R(f), m = R(p, !0);
			O(p);
			var h = z(p, 2), y = R(h), b = R(y);
			Wr(b), ze(2), O(y), O(h);
			var x = z(h, 2);
			O(f), O(n), wn(() => {
				yr(a, (X(t), Z(() => X(t).display_name || X(t).account_name))), yr(m, (X(t), Z(() => X(t).is_authenticated ? "Re-auth" : "Authorize"))), Gr(b, (X(t), Z(() => X(t).is_active)));
			}), ur("click", p, () => v(X(t).id)), ur("change", b, () => g(X(t).id, X(t).is_active)), ur("click", x, () => _(X(t).id, X(t).display_name || X(t).account_name)), $(e, n);
		}, (e) => {
			$(e, gi());
		}), O(ie), O(x), wn(() => {
			yr(m, X(d) ? "Expand" : "Collapse"), yr(w, `Accounts (${X(o), Z(() => X(o).length) ?? ""}/25)`);
		}), ur("click", f, () => F(d, !X(d))), $(e, t);
	};
	return kr(x, (e) => {
		X(l) ? e(S) : e(C, -1);
	}), O(b), $(e, b), qe(y);
}
customElements.define("spotify-dashboard-card", si(bi, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { bi as default };
